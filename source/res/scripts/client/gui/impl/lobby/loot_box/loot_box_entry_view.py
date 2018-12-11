# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/impl/lobby/loot_box/loot_box_entry_view.py
import logging
from collections import namedtuple
from account_helpers.settings_core import settings_constants
from account_helpers.settings_core.ServerSettingsManager import SETTINGS_SECTIONS
from frameworks.wulf import ViewFlags, Resource, WindowFlags
from gui import SystemMessages
from gui.impl.gen.resources import R
from gui.impl.gen.view_models.views.loot_box_entry_view_model import LootBoxEntryViewModel
from gui.impl.gen.view_models.views.loot_box_view.loot_box_selector_item_model import LootBoxSelectorItemModel
from gui.impl.gen.view_models.views.loot_box_view.loot_box_top_bar_item_model import LootBoxTopBarItemModel
from gui.impl.lobby.loot_box.loot_box_helper import MAX_BOXES_TO_OPEN, showLootBoxReward, showLootBoxMultyOpen
from gui.impl.lobby.loot_box.loot_box_helper import LootBoxShowHideCloseHandler
from gui.impl.lobby.tooltips.loot_box_category_tooltip import LootBoxCategoryTooltipContent
from gui.impl.pub import ViewImpl
from gui.impl.pub.lobby_window import LobbyWindow
from gui.impl.new_year.sounds import NewYearSoundsManager, RANDOM_STYLE_BOX
from gui.impl.lobby.loot_box.loot_box_sounds import onVideoStart, onVideoDone, LootBoxVideos
from gui.impl.lobby.loot_box.loot_box_sounds import LootBoxViewEvents, playSound
from gui.shared.gui_items.loot_box import NewYearCategories
from items.components.ny_constants import ToySettings
from gui.shared import EVENT_BUS_SCOPE, g_eventBus
from gui.shared import event_dispatcher
from gui.shared import events
from gui.shared.gui_items.loot_box import NewYearLootBoxes, GUI_ORDER, CATEGORIES_GUI_ORDER
from gui.shared.gui_items.processors.loot_boxes import LootBoxOpenProcessor
from gui.shared.utils import decorators
from helpers import dependency
from skeletons.account_helpers.settings_core import ISettingsCore
from skeletons.gui.game_control import IFestivityController
from skeletons.gui.lobby_context import ILobbyContext
from skeletons.gui.shared import IItemsCache
_logger = logging.getLogger(__name__)
_ContentState = namedtuple('_ContentState', ('boxInfoTextResource',
 'isOpenBoxBtnVisible',
 'isBackBtnVisible',
 'isBuyBoxBtnVisible',
 'isGiftBuyBtnVisible'))
_MAIN_CONTENT_STATES = {(NewYearLootBoxes.PREMIUM, True): _ContentState(Resource.INVALID, True, False, False, True),
 (NewYearLootBoxes.PREMIUM, False): _ContentState(None, False, True, True, False),
 (NewYearLootBoxes.COMMON, True): _ContentState(Resource.INVALID, True, False, False, False),
 (NewYearLootBoxes.COMMON, False): _ContentState(None, False, True, False, False)}
_MULTI_OPEN_COUNT_VISIBLE = 10

class LootBoxEntryView(ViewImpl):
    itemsCache = dependency.descriptor(IItemsCache)
    settingsCore = dependency.descriptor(ISettingsCore)
    lobbyContext = dependency.descriptor(ILobbyContext)
    _festivityController = dependency.descriptor(IFestivityController)
    __LOOT_BOX_CATEGORY_MAPPING = {NewYearCategories.NEWYEAR: ToySettings.NEW_YEAR,
     NewYearCategories.CHRISTMAS: ToySettings.CHRISTMAS,
     NewYearCategories.ORIENTAL: ToySettings.ORIENTAL,
     NewYearCategories.FAIRYTALE: ToySettings.FAIRYTALE}
    __slots__ = ('__isVideoOff', '__lastViewed', '__expectedViewed', '__availableBoxes', '__showHideCloseHandler')

    def __init__(self, *args, **kwargs):
        super(LootBoxEntryView, self).__init__(R.views.lootBoxEntryView, ViewFlags.VIEW, LootBoxEntryViewModel, *args, **kwargs)
        self.__isVideoOff = False
        self.__lastViewed = -1
        self.__expectedViewed = -1
        self.__availableBoxes = None
        self.__showHideCloseHandler = LootBoxShowHideCloseHandler()
        return

    @property
    def viewModel(self):
        return super(LootBoxEntryView, self).getViewModel()

    def createToolTipContent(self, event, contentID):
        return LootBoxCategoryTooltipContent(event.getArgument('category', '')) if contentID == R.views.lootBoxCategoryTooltipContent else super(LootBoxEntryView, self).createToolTipContent(event, contentID)

    def _initialize(self, *args, **kwargs):
        super(LootBoxEntryView, self)._initialize()
        self.__showHideCloseHandler.startListen(self.getParentWindow())
        self.viewModel.onOpenBoxBtnClick += self.__onOpenBox
        self.viewModel.onOpenBoxesBtnClick += self.__onOpenBoxes
        self.viewModel.onBuyBoxBtnClick += self.__onBuyBox
        self.viewModel.onCloseBtnClick += self.__onWindowClose
        self.viewModel.onBackToHangarBtnClick += self.__onBackToHangar
        self.viewModel.onVideoChangeClick += self.__onVideoChange
        self.viewModel.onBoxTypeSelected += self.__onBoxTypeSelected
        self.viewModel.onVideoStarted += self.__onVideoStarted
        self.viewModel.onVideoStopped += self.__onVideoStopped
        self.viewModel.needShowBlackOverlay += self.__needShowBlackOverlay
        self._festivityController.onStateChanged += self.__onStateChange
        self.itemsCache.onSyncCompleted += self.__onCacheResync
        self.settingsCore.onSettingsChanged += self.__updateVideoOff
        self.lobbyContext.getServerSettings().onServerSettingsChange += self.__onServerSettingChanged
        self.__isVideoOff = self.settingsCore.getSetting(settings_constants.GAME.LOOT_BOX_VIDEO_OFF)
        self.viewModel.setIsVideoOff(self.__isVideoOff)
        if args:
            initLootBoxType = args[0]
        else:
            _logger.warning('Initial tab is not specified.')
            initLootBoxType = NewYearLootBoxes.PREMIUM
        lootboxesCount = self.itemsCache.items.tokens.getLootBoxesTotalCount()
        lootBoxViewed = self.settingsCore.serverSettings.getSectionSettings(SETTINGS_SECTIONS.LOOT_BOX_VIEWED, 'count', 0)
        hasNewBoxes = lootboxesCount > lootBoxViewed
        isVideoPlaying = hasNewBoxes and not (self.__isVideoOff or initLootBoxType == NewYearLootBoxes.COMMON)
        self.viewModel.setIsVideoPlaying(isVideoPlaying)
        if not isVideoPlaying:
            self.viewModel.setIsNeedSetFocus(True)
        self.__availableBoxes = self.itemsCache.items.tokens.getLootBoxesCountByType()
        self.__setTopBarData()
        self.__setSelectorData(initLootBoxType)
        self.__updateLootBoxViewed()
        g_eventBus.handleEvent(events.LootboxesEvent(events.LootboxesEvent.ON_ENTRY_VIEW_LOADED), scope=EVENT_BUS_SCOPE.LOBBY)
        playSound(LootBoxViewEvents.ENTRY_VIEW_ENTER)

    def _finalize(self):
        playSound(LootBoxViewEvents.BENGAL_FIRE_OFF)
        self.__showHideCloseHandler.stopListen()
        self.__showHideCloseHandler = None
        self.viewModel.onOpenBoxBtnClick -= self.__onOpenBox
        self.viewModel.onOpenBoxesBtnClick -= self.__onOpenBoxes
        self.viewModel.onBuyBoxBtnClick -= self.__onBuyBox
        self.viewModel.onCloseBtnClick -= self.__onWindowClose
        self.viewModel.onBackToHangarBtnClick -= self.__onBackToHangar
        self.viewModel.onVideoChangeClick -= self.__onVideoChange
        self.viewModel.onBoxTypeSelected -= self.__onBoxTypeSelected
        self.viewModel.onVideoStarted -= self.__onVideoStarted
        self.viewModel.onVideoStopped -= self.__onVideoStopped
        self.viewModel.needShowBlackOverlay -= self.__needShowBlackOverlay
        self._festivityController.onStateChanged -= self.__onStateChange
        self.itemsCache.onSyncCompleted -= self.__onCacheResync
        self.settingsCore.onSettingsChanged -= self.__updateVideoOff
        self.lobbyContext.getServerSettings().onServerSettingsChange -= self.__onServerSettingChanged
        self.__removeEventBusHandlers()
        self.settingsCore.applyStorages(False)
        super(LootBoxEntryView, self)._finalize()
        return

    def __onBoxTypeSelected(self, _=None):
        self.__updateMainContent()

    def __onCacheResync(self, *_):
        self.__update()

    def __update(self):
        self.__availableBoxes = self.itemsCache.items.tokens.getLootBoxesCountByType()
        self.__updateLootBoxViewed()
        self.__updateSelectorData()
        self.__updateTopBarData()

    def __updateVideoOff(self, diff):
        if settings_constants.GAME.LOOT_BOX_VIDEO_OFF in diff:
            self.__isVideoOff = diff[settings_constants.GAME.LOOT_BOX_VIDEO_OFF]
            self.viewModel.setIsVideoOff(self.__isVideoOff)

    def __updateLootBoxViewed(self):
        totalCount = self.itemsCache.items.tokens.getLootBoxesTotalCount()
        if self.__expectedViewed != -1 and self.__expectedViewed != totalCount:
            return
        if self.__lastViewed != -1 and self.__lastViewed == totalCount:
            return
        self.__lastViewed = totalCount
        self.__expectedViewed = totalCount
        self.settingsCore.serverSettings.setSectionSettings(SETTINGS_SECTIONS.LOOT_BOX_VIEWED, {'count': self.__lastViewed})

    def __setSelectorData(self, initLootBoxType):
        boxItems = self.viewModel.boxSelector.getItems()
        for idx, lootBoxType in enumerate(GUI_ORDER):
            selectorItem = LootBoxSelectorItemModel()
            with selectorItem.transaction() as itemTx:
                itemTx.setBoxName(R.strings.lootboxes.type.dyn(lootBoxType))
                itemTx.setBoxType(lootBoxType)
                itemTx.setIndex(idx)
                if lootBoxType in self.__availableBoxes:
                    itemTx.setBoxCounter(self.__availableBoxes[lootBoxType]['total'])
                else:
                    itemTx.setBoxCounter(0)
            boxItems.addViewModel(selectorItem)
            if initLootBoxType == lootBoxType:
                self.viewModel.boxSelector.addSelectedIndex(idx)

        self.__updateMainContent()

    def __setTopBarData(self):
        barItems = self.viewModel.topBar.getItems()
        premiumBoxes = self.__availableBoxes.get(NewYearLootBoxes.PREMIUM)
        if not premiumBoxes:
            _logger.error('No premium loot boxes in the config!')
            return
        else:
            defaultIndex = None
            countInCategories = premiumBoxes['categories']
            for idx, category in enumerate(CATEGORIES_GUI_ORDER):
                counter = countInCategories.get(category, 0)
                if defaultIndex is None and counter:
                    defaultIndex = idx
                barItem = LootBoxTopBarItemModel()
                with barItem.transaction() as itemTx:
                    itemTx.setBoxType(category)
                    itemTx.setBoxCounter(counter)
                barItems.addViewModel(barItem)

            if defaultIndex is None:
                self.viewModel.topBar.addSelectedIndex(0)
            else:
                self.viewModel.topBar.addSelectedIndex(defaultIndex)
            return

    def __updateSelectorData(self):
        boxModels = self.viewModel.boxSelector.getItems()
        for boxModel in boxModels:
            lootBoxType = boxModel.getBoxType()
            if lootBoxType in self.__availableBoxes:
                boxModel.setBoxCounter(self.__availableBoxes[lootBoxType]['total'])
            boxModel.setBoxCounter(0)

        if not self.__updateEmptyState():
            self.__updateMainContent()

    def __updateTopBarData(self):
        premiumBoxes = self.__availableBoxes.get(NewYearLootBoxes.PREMIUM)
        if not premiumBoxes:
            _logger.error('No premium loot boxes in the config!')
            for barModel in self.viewModel.topBar.getItems():
                barModel.setBoxCounter(0)

            return
        countInCategories = premiumBoxes['categories']
        topBarItems = self.viewModel.topBar.getItems()
        for barModel in topBarItems:
            category = barModel.getBoxType()
            barModel.setBoxCounter(countInCategories.get(category, 0))

    def __updateMainContent(self):
        with self.viewModel.transaction() as model:
            selectedIdx = model.boxSelector.getSelectedIndices()[0]
            selectedItem = model.boxSelector.getSelectedItem()
            model.setCurrentIndex(selectedIdx)
            boxType = selectedItem.getBoxType()
            if self.viewModel.topBar.getSelectedItem() is not None:
                category = self.viewModel.topBar.getSelectedItem().getBoxType()
            else:
                category = ''
            if boxType in self.__availableBoxes:
                available = self.__availableBoxes[boxType]
                categories = available['categories']
                if boxType == NewYearLootBoxes.PREMIUM:
                    boxNumber = categories[category] if category in categories else available['total']
                else:
                    boxNumber = available['total']
            else:
                boxNumber = 0
            hasBoxes = boxNumber > 0
            selectedBoxCategory = ''
            if hasBoxes:
                if category and boxType == NewYearLootBoxes.PREMIUM:
                    selectedBoxCategory = category
                    icon = R.images.gui.maps.icons.lootboxes.category.big.dyn(boxType).dyn(category)
                else:
                    icon = R.images.gui.maps.icons.lootboxes.types.big.dyn(boxType)
            else:
                if category and boxType == NewYearLootBoxes.PREMIUM:
                    selectedBoxCategory = category
                icon = Resource.INVALID
            model.setSelectedBoxIcon(icon)
            model.setSelectedBoxType(boxType)
            model.setSelectedBoxCategory(selectedBoxCategory)
            contentState = _MAIN_CONTENT_STATES[boxType, hasBoxes]
            if contentState.boxInfoTextResource is not None:
                model.setBoxInformation(contentState.boxInfoTextResource)
            else:
                model.setBoxInformation(R.strings.lootboxes.entryView.ended.dyn(boxType))
            model.setIsOpenBoxBtnVisible(contentState.isOpenBoxBtnVisible)
            model.setIsBackBtnVisible(contentState.isBackBtnVisible)
            model.setIsBuyBoxBtnVisible(contentState.isBuyBoxBtnVisible)
            model.setIsGiftBuyBtnVisible(contentState.isGiftBuyBtnVisible)
            model.setOpenBoxesCounter(MAX_BOXES_TO_OPEN if boxNumber > MAX_BOXES_TO_OPEN else boxNumber)
            model.setIsMulitOpenBtnVisible(boxNumber >= _MULTI_OPEN_COUNT_VISIBLE)
            model.setIsTopBarVisible(boxType == NewYearLootBoxes.PREMIUM)
        setting = self.__LOOT_BOX_CATEGORY_MAPPING.get(category) if category else None
        NewYearSoundsManager.setStylesSwitchBox(setting if setting else RANDOM_STYLE_BOX)
        return

    def __onOpenBox(self, _=None):
        box = self.__getSelectedBox()
        if box is None:
            _logger.error('Can not open the selected lootbox!')
            self.__switchBlackOverlay(False)
            return
        else:
            self.__requestLootBoxOpen(box)
            return

    def __onOpenBoxes(self, _=None):
        box = self.__getSelectedBox()
        if box is None:
            _logger.error('Can not open several boxes!')
            self.__switchBlackOverlay(False)
            return
        else:
            invCount = box.getInventoryCount()
            openCount = MAX_BOXES_TO_OPEN if invCount > MAX_BOXES_TO_OPEN else invCount
            self.__requestLootBoxOpen(box, openCount)
            return

    def __getSelectedBox(self):
        selectedType = self.viewModel.boxSelector.getSelectedItem().getBoxType()
        boxes = self.itemsCache.items.tokens.getLootBoxes().values()
        for box in boxes:
            if box.getType() == selectedType and box.getInventoryCount() > 0:
                if selectedType == NewYearLootBoxes.PREMIUM:
                    selectedCategory = self.viewModel.topBar.getSelectedItem().getBoxType()
                    if selectedCategory == box.getCategory():
                        return box
                else:
                    return box

        return None

    def __onBuyBox(self, _=None):
        event_dispatcher.showLootBoxBuyWindow()

    def __onWindowClose(self, _=None):
        playSound(LootBoxViewEvents.ENTRY_VIEW_EXIT)
        self.destroyWindow()

    def __onBackToHangar(self, _=None):
        self.destroyWindow()
        event_dispatcher.showHangar()

    def __onVideoStarted(self, _=None):
        onVideoStart(LootBoxVideos.NEW_BOX)

    def __onVideoStopped(self, _=None):
        self.__stopVideoPlaying()

    def __onVideoChange(self, _=None):
        self.__stopVideoPlaying()
        self.settingsCore.applySetting(settings_constants.GAME.LOOT_BOX_VIDEO_OFF, not self.__isVideoOff)

    def __stopVideoPlaying(self):
        onVideoDone()
        self.viewModel.setIsVideoPlaying(False)
        self.viewModel.setIsNeedSetFocus(True)

    def __needShowBlackOverlay(self, _=None):
        self.__switchBlackOverlay(True)

    @decorators.process('updating')
    def __requestLootBoxOpen(self, boxItem, count=1):
        self.__expectedViewed = self.__lastViewed - count
        result = yield LootBoxOpenProcessor(boxItem, count).request()
        if result:
            if result.userMsg:
                SystemMessages.pushI18nMessage(result.userMsg, type=result.sysMsgType)
            if result.success:
                rewardsList = result.auxData
                if not rewardsList:
                    _logger.error('Lootbox is opened, but no rewards has been received.')
                    self.__switchBlackOverlay(False)
                elif len(rewardsList) == 1:
                    showLootBoxReward(boxItem, rewardsList[0])
                else:
                    showLootBoxMultyOpen(boxItem, rewardsList)
            else:
                self.__switchBlackOverlay(False)
        else:
            self.__switchBlackOverlay(False)

    def __onServerSettingChanged(self, diff):
        if 'lootBoxes_config' in diff:
            self.__update()
        if not self.lobbyContext.getServerSettings().isLootBoxesEnabled():
            self.destroyWindow()

    def __onStateChange(self):
        if not self._festivityController.isEnabled():
            self.destroyWindow()

    def __handleRewardViewHide(self, _):
        self.__switchBlackOverlay(False)

    def __handleCloseToHangar(self, _):
        self.__onWindowClose()

    def __handleMultiOpenViewHide(self, _):
        self.__switchBlackOverlay(False)

    def __switchBlackOverlay(self, value):
        if value:
            g_eventBus.addListener(events.LootboxesEvent.ON_MULTI_OPEN_VIEW_CLOSED, self.__handleMultiOpenViewHide, scope=EVENT_BUS_SCOPE.LOBBY)
            g_eventBus.addListener(events.LootboxesEvent.ON_REWARD_VIEW_CLOSED, self.__handleRewardViewHide, scope=EVENT_BUS_SCOPE.LOBBY)
        else:
            self.__removeEventBusHandlers()
        self.viewModel.setShowBlackOverlay(value)

    def __removeEventBusHandlers(self):
        g_eventBus.removeListener(events.LootboxesEvent.ON_MULTI_OPEN_VIEW_CLOSED, self.__handleMultiOpenViewHide, scope=EVENT_BUS_SCOPE.LOBBY)
        g_eventBus.removeListener(events.LootboxesEvent.ON_REWARD_VIEW_CLOSED, self.__handleRewardViewHide, scope=EVENT_BUS_SCOPE.LOBBY)

    def __updateEmptyState(self):
        hasBoxesBefore = self.viewModel.getIsOpenBoxBtnVisible()
        selectedItem = self.viewModel.boxSelector.getSelectedItem()
        boxType = selectedItem.getBoxType()
        if self.viewModel.topBar.getSelectedItem() is not None:
            category = self.viewModel.topBar.getSelectedItem().getBoxType()
        else:
            category = ''
        if boxType in self.__availableBoxes:
            available = self.__availableBoxes[boxType]
            categories = available['categories']
            if boxType == NewYearLootBoxes.PREMIUM:
                boxNumber = categories[category] if category in categories else available['total']
            else:
                boxNumber = available['total']
        else:
            boxNumber = 0
        hasBoxesAfter = boxNumber > 0
        isEmptySwitch = hasBoxesBefore != hasBoxesAfter
        if isEmptySwitch:
            self.viewModel.setIsEmptySwitch(True)
        return isEmptySwitch


class LootBoxEntryWindow(LobbyWindow):
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        super(LootBoxEntryWindow, self).__init__(wndFlags=WindowFlags.OVERLAY, decorator=None, content=LootBoxEntryView(*args, **kwargs), parent=None)
        return
