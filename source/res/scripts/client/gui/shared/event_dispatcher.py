# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/shared/event_dispatcher.py
import logging
from operator import attrgetter
from CurrentVehicle import HeroTankPreviewAppearance
from adisp import process
from constants import RentType, GameSeasonType
from debug_utils import LOG_WARNING
from frameworks.wulf import ViewStatus
from gui import SystemMessages, DialogsInterface, GUI_SETTINGS
from gui.Scaleform import MENU
from gui.Scaleform.daapi.view.dialogs.ConfirmModuleMeta import SellModuleMeta
from gui.Scaleform.genConsts.STORAGE_CONSTANTS import STORAGE_CONSTANTS
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.Scaleform.framework import ScopeTemplates
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.dialogs import I18nInfoDialogMeta, I18nConfirmDialogMeta, DIALOG_BUTTON_ID
from gui.Scaleform.daapi.view.dialogs.ExchangeDialogMeta import ExchangeCreditsWebProductMeta
from gui.Scaleform.daapi.view.dialogs.rent_confirm_dialog import RentConfirmDialogMeta
from gui.Scaleform.daapi.view.lobby.referral_program.referral_program_helpers import getReferralProgramURL
from gui.Scaleform.daapi.view.lobby.store.browser.ingameshop_helpers import getWebShopURL, isIngameShopEnabled, getBuyPremiumUrl
from gui.Scaleform.framework.entities.View import ViewKey
from gui.Scaleform.genConsts.BOOSTER_CONSTANTS import BOOSTER_CONSTANTS
from gui.Scaleform.genConsts.CLANS_ALIASES import CLANS_ALIASES
from gui.Scaleform.genConsts.EPICBATTLES_ALIASES import EPICBATTLES_ALIASES
from gui.Scaleform.genConsts.PERSONAL_MISSIONS_ALIASES import PERSONAL_MISSIONS_ALIASES
from gui.Scaleform.genConsts.RANKEDBATTLES_ALIASES import RANKEDBATTLES_ALIASES
from gui.impl import backport
from gui.game_control.links import URLMacros
from gui.impl.pub import UIImplType
from gui.ingame_shop import generateShopRentRenewProductID, showBuyGoldForRentWebOverlay
from gui.ingame_shop import getShopProductInfo
from gui.ingame_shop import makeBuyParamsByProductInfo
from gui.ingame_shop import showBuyVehicleOverlay
from gui.impl.gen import R
from gui.prb_control.settings import CTRL_ENTITY_TYPE
from gui.shared import events, g_eventBus, money
from gui.shared.event_bus import EVENT_BUS_SCOPE
from gui.shared.formatters import text_styles
from gui.shared.gui_items.loot_box import NewYearLootBoxes
from gui.shared.gui_items.processors.goodies import BoosterActivator
from gui.shared.money import Currency
from gui.shared.notifications import NotificationPriorityLevel
from gui.shared.utils import isPopupsWindowsOpenDisabled
from gui.shared.utils.functions import getViewName, getUniqueViewName
from gui.shared.utils.requesters import REQ_CRITERIA
from gui.shared.gui_items.Vehicle import getUserName
from items import vehicles as vehicles_core
from helpers import dependency
from helpers.aop import pointcutable
from helpers.i18n import makeString as _ms
from ny_common.settings import NYLootBoxConsts
from skeletons.gui.app_loader import IAppLoader
from skeletons.gui.game_control import IHeroTankController, IReferralProgramController, IEpicBattleMetaGameController
from skeletons.gui.impl import IGuiLoader
from skeletons.gui.shared import IItemsCache
from skeletons.gui.goodies import IGoodiesCache
from skeletons.gui.lobby_context import ILobbyContext
from skeletons.new_year import INewYearController
from soft_exception import SoftException
from async import async, await
_logger = logging.getLogger(__name__)

class SETTINGS_TAB_INDEX(object):
    GAME = 0
    GRAPHICS = 1
    SOUND = 2
    CONTROL = 3
    AIM = 4
    MARKERS = 5
    FEEDBACK = 6


def showBattleResultsWindow(arenaUniqueID):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.BATTLE_RESULTS, getViewName(VIEW_ALIAS.BATTLE_RESULTS, str(arenaUniqueID)), {'arenaUniqueID': arenaUniqueID}), EVENT_BUS_SCOPE.LOBBY)


def notifyBattleResultsPosted(arenaUniqueID):
    g_eventBus.handleEvent(events.LobbySimpleEvent(events.LobbySimpleEvent.BATTLE_RESULTS_POSTED, {'arenaUniqueID': arenaUniqueID}), EVENT_BUS_SCOPE.LOBBY)


def showRankedBattleResultsWindow(rankedResultsVO, rankInfo, questsProgress):
    g_eventBus.handleEvent(events.LoadViewEvent(alias=RANKEDBATTLES_ALIASES.RANKED_BATTLES_BATTLE_RESULTS, ctx={'rankedResultsVO': rankedResultsVO,
     'rankInfo': rankInfo,
     'questsProgress': questsProgress}), EVENT_BUS_SCOPE.LOBBY)


def showRankedAwardWindow(awardsSequence, rankedInfo):
    g_eventBus.handleEvent(events.LoadViewEvent(alias=RANKEDBATTLES_ALIASES.RANKED_BATTLES_AWARD, ctx={'awardsSequence': awardsSequence,
     'rankedInfo': rankedInfo}), EVENT_BUS_SCOPE.LOBBY)


def showRankedPrimeTimeWindow():
    g_eventBus.handleEvent(events.LoadViewEvent(alias=RANKEDBATTLES_ALIASES.RANKED_BATTLE_PRIME_TIME, ctx={}), EVENT_BUS_SCOPE.LOBBY)


def showEpicBattlesPrimeTimeWindow():
    g_eventBus.handleEvent(events.LoadViewEvent(alias=EPICBATTLES_ALIASES.EPIC_BATTLES_PRIME_TIME_ALIAS, ctx={}), EVENT_BUS_SCOPE.LOBBY)


def showFrontlineBuyConfirmView(ctx):
    g_eventBus.handleEvent(events.LoadViewEvent(alias=EPICBATTLES_ALIASES.FRONTLINE_BUY_CONFIRM_VIEW_ALIAS, ctx=ctx), EVENT_BUS_SCOPE.LOBBY)


def showEpicBattlesWelcomeBackWindow():
    g_eventBus.handleEvent(events.LoadViewEvent(alias=EPICBATTLES_ALIASES.EPIC_BATTLES_WELCOME_BACK_ALIAS, ctx={}), EVENT_BUS_SCOPE.LOBBY)


def showEpicBattlesAfterBattleWindow(reusableInfo):
    g_eventBus.handleEvent(events.LoadViewEvent(alias=EPICBATTLES_ALIASES.EPIC_BATTLES_AFTER_BATTLE_ALIAS, ctx={'reusableInfo': reusableInfo}), EVENT_BUS_SCOPE.LOBBY)


def showVehicleInfo(vehTypeCompDescr):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.VEHICLE_INFO_WINDOW, getViewName(VIEW_ALIAS.VEHICLE_INFO_WINDOW, int(vehTypeCompDescr)), ctx={'vehicleCompactDescr': int(vehTypeCompDescr)}), EVENT_BUS_SCOPE.LOBBY)


def showVehicleRentDialog(intCD, rentType, nums, seasonType, price, buyParams):
    if not (seasonType == GameSeasonType.EPIC and rentType in (RentType.SEASON_RENT, RentType.SEASON_CYCLE_RENT)):
        _logger.debug('GameSeasonType %s with RentType %s is not supported', seasonType, rentType)
        return
    _purchaseOffer(intCD, rentType, nums, price, seasonType, buyParams, renew=False)


@process
def showVehicleRentRenewDialog(intCD, rentType, num, seasonType):
    if not (seasonType == GameSeasonType.EPIC and rentType == RentType.SEASON_CYCLE_RENT):
        _logger.debug('GameSeasonType %s with RentType %s is not supported', seasonType, rentType)
        return
    productID = generateShopRentRenewProductID(intCD, rentType, num, seasonType)
    productInfo = yield getShopProductInfo(productID)
    if not productInfo:
        SystemMessages.pushMessage(_ms(MESSENGER.SERVER_ERRORS_INTERNALERROR_MESSAGE), type=SystemMessages.SM_TYPE.Error)
        return
    buyParams = makeBuyParamsByProductInfo(productInfo)
    _purchaseOffer(intCD, rentType, [num], productInfo.price, seasonType, buyParams, renew=True)


@process
@dependency.replace_none_kwargs(itemsCache=IItemsCache)
def _purchaseOffer(vehicleCD, rentType, nums, price, seasonType, buyParams, renew, itemsCache=None):
    if mayObtainForMoney(price):
        _doPurchaseOffer(vehicleCD, rentType, nums, price, seasonType, buyParams, renew)
    elif mayObtainWithMoneyExchange(price):
        vehicle = itemsCache.items.getItemByCD(vehicleCD)
        isOk, _ = yield DialogsInterface.showDialog(ExchangeCreditsWebProductMeta(name=vehicle.shortUserName if vehicle else '', count=1, price=price.get(Currency.CREDITS)))
        if isOk:
            _doPurchaseOffer(vehicleCD, rentType, nums, price, seasonType, buyParams, renew)
    elif price.getCurrency() == Currency.GOLD and isIngameShopEnabled():
        showBuyGoldForRentWebOverlay(price.get(Currency.GOLD), vehicleCD)
    else:
        vehicleName = getUserName(vehicles_core.getVehicleType(vehicleCD))
        SystemMessages.pushMessage(backport.text(R.strings.system_messages.vehicle_rent.dyn('not_enough_{}'.format(price.getCurrency()))(), vehName=vehicleName), type=SystemMessages.SM_TYPE.Error)


@process
def _doPurchaseOffer(vehicleCD, rentType, nums, price, seasonType, buyParams, renew):
    requestConfirmed = yield DialogsInterface.showDialog(meta=RentConfirmDialogMeta(vehicleCD, rentType, nums, price, seasonType, renew))
    if requestConfirmed:
        if mayObtainForMoney(price):
            showBuyVehicleOverlay(buyParams)
        else:
            _purchaseOffer(vehicleCD, rentType, nums, price, seasonType, buyParams, renew)


@dependency.replace_none_kwargs(itemsCache=IItemsCache)
def mayObtainWithMoneyExchange(itemPrice, itemsCache=None):
    return itemPrice <= itemsCache.items.stats.money.exchange(Currency.GOLD, Currency.CREDITS, itemsCache.items.shop.exchangeRate, default=0)


@dependency.replace_none_kwargs(itemsCache=IItemsCache)
def mayObtainForMoney(itemPrice, itemsCache=None):
    return itemPrice <= itemsCache.items.stats.money


def showModuleInfo(itemCD, vehicleDescr):
    itemCD = int(itemCD)
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.MODULE_INFO_WINDOW, getViewName(VIEW_ALIAS.MODULE_INFO_WINDOW, itemCD), {'moduleCompactDescr': itemCD,
     'vehicleDescr': vehicleDescr}), EVENT_BUS_SCOPE.LOBBY)


def showStorageModuleInfo(intCD):
    intCD = int(intCD)
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.MODULE_INFO_WINDOW, getViewName(VIEW_ALIAS.MODULE_INFO_WINDOW, intCD), {'moduleCompactDescr': intCD,
     'isAdditionalInfoShow': _ms(MENU.MODULEINFO_ADDITIONALINFO)}), EVENT_BUS_SCOPE.LOBBY)


def showStorageBoosterInfo(boosterID):
    boosterID = int(boosterID)
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.BOOSTER_INFO_WINDOW, getViewName(VIEW_ALIAS.BOOSTER_INFO_WINDOW, boosterID), {'boosterID': boosterID}), EVENT_BUS_SCOPE.LOBBY)


def showVehicleSellDialog(vehInvID):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.VEHICLE_SELL_DIALOG, ctx={'vehInvID': int(vehInvID)}), EVENT_BUS_SCOPE.LOBBY)


def showVehicleBuyDialog(vehicle, actionType=None, isTradeIn=False, previousAlias=None, showOnlyCongrats=False, ctx=None):
    from gui.impl.lobby.buy_vehicle_view import BuyVehicleWindow
    ctx = ctx or {}
    ctx.update({'nationID': vehicle.nationID,
     'itemID': vehicle.innationID,
     'actionType': actionType,
     'isTradeIn': isTradeIn,
     'previousAlias': previousAlias,
     'showOnlyCongrats': showOnlyCongrats})
    window = BuyVehicleWindow(ctx=ctx)
    window.load()
    if showOnlyCongrats:
        window.showCongratulations()


@dependency.replace_none_kwargs(itemsCache=IItemsCache)
def showBlueprintView(vehicleCD, exitEvent=None, itemsCache=None):
    from gui.impl.lobby.blueprints.blueprint_screen import BlueprintScreen
    exitEvent = exitEvent or events.LoadViewEvent(VIEW_ALIAS.LOBBY_TECHTREE, ctx={'nation': itemsCache.items.getItemByCD(vehicleCD).nationName,
     'blueprintMode': True})
    g_eventBus.handleEvent(events.LoadUnboundViewEvent(R.views.lobby.blueprints.blueprint_screen.blueprint_screen.BlueprintScreen(), BlueprintScreen, ScopeTemplates.LOBBY_SUB_SCOPE, ctx={'vehicleCD': vehicleCD,
     'exitEvent': exitEvent}), scope=EVENT_BUS_SCOPE.LOBBY)


def showChangeVehicleNationDialog(vehicleCD):
    from gui.impl.lobby.nation_change.nation_change_screen import NationChangeScreen
    g_eventBus.handleEvent(events.LoadUnboundViewEvent(R.views.lobby.nation_change.nation_change_screen.NationChangeScreen(), NationChangeScreen, ScopeTemplates.LOBBY_SUB_SCOPE, ctx={'vehicleCD': vehicleCD}), scope=EVENT_BUS_SCOPE.LOBBY)


def showPiggyBankView():
    from gui.impl.lobby.premacc.piggybank import PiggyBankView
    g_eventBus.handleEvent(events.LoadUnboundViewEvent(R.views.lobby.premacc.piggybank.Piggybank(), PiggyBankView, ScopeTemplates.LOBBY_SUB_SCOPE), scope=EVENT_BUS_SCOPE.LOBBY)


def showMapsBlacklistView():
    from gui.impl.lobby.premacc.maps_blacklist_view import MapsBlacklistView
    g_eventBus.handleEvent(events.LoadUnboundViewEvent(layoutID=R.views.lobby.premacc.maps_blacklist_view.MapsBlacklistView(), viewClass=MapsBlacklistView, scope=ScopeTemplates.LOBBY_SUB_SCOPE), scope=EVENT_BUS_SCOPE.LOBBY)


def showDailyExpPageView(exitEvent=None):
    from gui.impl.lobby.premacc.daily_experience_view import DailyExperienceView
    exitEvent = exitEvent or events.LoadViewEvent(VIEW_ALIAS.LOBBY_HANGAR)
    g_eventBus.handleEvent(events.LoadUnboundViewEvent(layoutID=R.views.lobby.premacc.daily_experience_view.DailyExperiencePage(), viewClass=DailyExperienceView, scope=ScopeTemplates.LOBBY_SUB_SCOPE, ctx={'exitEvent': exitEvent}), scope=EVENT_BUS_SCOPE.LOBBY)


def showDashboardView():
    from gui.impl.lobby.premacc.prem_dashboard_view import PremDashboardView
    g_eventBus.handleEvent(events.LoadUnboundViewEvent(R.views.lobby.premacc.prem_dashboard_view.PremDashboardView(), PremDashboardView, ScopeTemplates.LOBBY_SUB_SCOPE), scope=EVENT_BUS_SCOPE.LOBBY)


def gamefaceEnabled():
    lobbyContext = dependency.instance(ILobbyContext)
    guiLoader = dependency.instance(IGuiLoader)
    isGamefaceInitilized = guiLoader.implTypeMask & UIImplType.GAMEFACE_UI_IMPL > 0
    isGamefaceEnabled = lobbyContext.getServerSettings().isGamefaceEnabled()
    return isGamefaceInitilized and isGamefaceEnabled


@async
def showBattleBoosterBuyDialog(battleBoosterIntCD, install=False):
    from gui.impl.dialogs import dialogs
    from gui.impl.lobby.instructions.booster_buy_dialog import BoosterBuyWindowView
    if gamefaceEnabled():
        yield dialogs.showSimple(BoosterBuyWindowView(battleBoosterIntCD, install))
    else:
        g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.BOOSTER_BUY_WINDOW, ctx={'typeCompDescr': battleBoosterIntCD,
         'install': install}), EVENT_BUS_SCOPE.LOBBY)


@async
def _showBattleBoosterGFSellDialog(battleBoosterIntCD):
    from gui.impl.lobby.instructions.booster_sell_dialog import BoosterSellWindowView
    from gui.impl.dialogs import dialogs
    yield dialogs.showSimple(BoosterSellWindowView(battleBoosterIntCD))


@process
def showBattleBoosterSellDialog(battleBoosterIntCD):
    if gamefaceEnabled():
        _showBattleBoosterGFSellDialog(battleBoosterIntCD)
    else:
        yield DialogsInterface.showDialog(SellModuleMeta(battleBoosterIntCD))


def showResearchView(vehTypeCompDescr, exitEvent=None):
    exitEvent = exitEvent or events.LoadViewEvent(VIEW_ALIAS.LOBBY_HANGAR)
    loadEvent = events.LoadViewEvent(VIEW_ALIAS.LOBBY_RESEARCH, ctx={'rootCD': vehTypeCompDescr,
     'exit': exitEvent})
    g_eventBus.handleEvent(loadEvent, scope=EVENT_BUS_SCOPE.LOBBY)


@dependency.replace_none_kwargs(itemsCache=IItemsCache)
def showTechTree(vehTypeCompDescr=None, itemsCache=None):
    vehicle = itemsCache.items.getItemByCD(vehTypeCompDescr)
    nation = vehicle.nationName
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.LOBBY_TECHTREE, ctx={'nation': nation}), scope=EVENT_BUS_SCOPE.LOBBY)


def showVehicleStats(vehTypeCompDescr):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.LOBBY_PROFILE, ctx={'itemCD': vehTypeCompDescr}), scope=EVENT_BUS_SCOPE.LOBBY)


def showHangar():
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.LOBBY_HANGAR), scope=EVENT_BUS_SCOPE.LOBBY)


def showBarracks():
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.LOBBY_BARRACKS), scope=EVENT_BUS_SCOPE.LOBBY)


def showBadges(backViewName=''):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.BADGES_PAGE, ctx={'backViewName': backViewName} if backViewName else None), scope=EVENT_BUS_SCOPE.LOBBY)
    return


def showStrongholds(url=None):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.LOBBY_STRONGHOLD, ctx={'url': url}), scope=EVENT_BUS_SCOPE.LOBBY)


def openManualPage(chapterIndex):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.MANUAL_CHAPTER_VIEW, ctx={'chapterIndex': chapterIndex}), EVENT_BUS_SCOPE.LOBBY)


@process
def showWebShop(url='', path='', params=None):
    parse = URLMacros().parse
    if path:
        path = yield parse(path, params)
        if url:
            url = yield parse(url)
        else:
            url = getWebShopURL()
    else:
        path = ''
        if url:
            url = yield parse(url, params)
        else:
            url = getWebShopURL()
    url = '/'.join((node.strip('/') for node in (url, path)))
    appLoader = dependency.instance(IAppLoader)
    app = appLoader.getApp()
    if app is not None and app.containerManager is not None:
        viewKey = ViewKey(VIEW_ALIAS.LOBBY_STORE)
        browserWindow = app.containerManager.getViewByKey(viewKey)
        if browserWindow is not None:
            browser = browserWindow.getBrowser()
            browser.navigate(url)
            return
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.LOBBY_STORE, ctx={'url': url}), scope=EVENT_BUS_SCOPE.LOBBY)
    return


def showOldShop(ctx=None):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.LOBBY_STORE_OLD, ctx=ctx), scope=EVENT_BUS_SCOPE.LOBBY)


def showStorage(defaultSection=STORAGE_CONSTANTS.FOR_SELL, tabId=None):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.LOBBY_STORAGE, ctx={'defaultSection': defaultSection,
     'defaultTab': tabId}), scope=EVENT_BUS_SCOPE.LOBBY)


def showOldVehiclePreview(vehTypeCompDescr, previewAlias=VIEW_ALIAS.LOBBY_HANGAR, vehStrCD=None, previewBackCb=None):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.VEHICLE_PREVIEW, ctx={'itemCD': vehTypeCompDescr,
     'previewAlias': previewAlias,
     'vehicleStrCD': vehStrCD,
     'previewBackCb': previewBackCb}), scope=EVENT_BUS_SCOPE.LOBBY)


def showVehiclePreview(vehTypeCompDescr, previewAlias=VIEW_ALIAS.LOBBY_HANGAR, vehStrCD=None, previewBackCb=None, itemsPack=None, offers=None, price=money.MONEY_UNDEFINED, oldPrice=None, title='', description=None, endTime=None, buyParams=None, vehParams=None, isFrontline=False):
    itemsCache = dependency.instance(IItemsCache)
    lobbyContext = dependency.instance(ILobbyContext)
    newPreviewEnabled = lobbyContext.getServerSettings().isIngamePreviewEnabled()
    heroTankController = dependency.instance(IHeroTankController)
    heroTankCD = heroTankController.getCurrentTankCD()
    isHeroTank = heroTankCD and heroTankCD == vehTypeCompDescr
    if isHeroTank and not (itemsPack or offers):
        goToHeroTankOnScene(vehTypeCompDescr, previewAlias)
    elif isFrontline:
        g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.FRONTLINE_VEHICLE_PREVIEW_20, ctx={'itemCD': vehTypeCompDescr,
         'previewAlias': previewAlias,
         'previewBackCb': previewBackCb}), scope=EVENT_BUS_SCOPE.LOBBY)
    elif newPreviewEnabled:
        vehicle = itemsCache.items.getItemByCD(vehTypeCompDescr)
        if not (itemsPack or offers) and vehicle.canTradeIn:
            viewAlias = VIEW_ALIAS.TRADE_IN_VEHICLE_PREVIEW_20
        else:
            viewAlias = VIEW_ALIAS.VEHICLE_PREVIEW_20
        g_eventBus.handleEvent(events.LoadViewEvent(viewAlias, ctx={'itemCD': vehTypeCompDescr,
         'previewAlias': previewAlias,
         'vehicleStrCD': vehStrCD,
         'previewBackCb': previewBackCb,
         'itemsPack': itemsPack,
         'offers': offers,
         'price': price,
         'oldPrice': oldPrice,
         'title': title,
         'description': description,
         'endTime': endTime,
         'buyParams': buyParams,
         'vehParams': vehParams}), scope=EVENT_BUS_SCOPE.LOBBY)
    elif itemsPack or offers:
        SystemMessages.pushMessage(text=_ms(MESSENGER.CLIENT_ERROR_SHARED_TRY_LATER), type=SystemMessages.SM_TYPE.Error, priority=NotificationPriorityLevel.MEDIUM)
    else:
        showOldVehiclePreview(vehTypeCompDescr, previewAlias, vehStrCD, previewBackCb)


def goToHeroTankOnScene(vehTypeCompDescr, previewAlias=VIEW_ALIAS.LOBBY_HANGAR):
    import BigWorld
    from HeroTank import HeroTank
    from ClientSelectableCameraObject import ClientSelectableCameraObject
    for entity in BigWorld.entities.values():
        if entity and isinstance(entity, HeroTank):
            showHeroTankPreview(vehTypeCompDescr, previewAlias=previewAlias, previousBackAlias=None)
            ClientSelectableCameraObject.switchCamera(entity)
            break

    return


def showHeroTankPreview(vehTypeCompDescr, previewAlias=VIEW_ALIAS.LOBBY_HANGAR, previousBackAlias=None):
    lobbyContext = dependency.instance(ILobbyContext)
    if lobbyContext.getServerSettings().isIngamePreviewEnabled():
        alias = VIEW_ALIAS.HERO_VEHICLE_PREVIEW_20
    else:
        alias = VIEW_ALIAS.HERO_VEHICLE_PREVIEW
    g_eventBus.handleEvent(events.LoadViewEvent(alias, ctx={'itemCD': vehTypeCompDescr,
     'previewAlias': previewAlias,
     'previewAppearance': HeroTankPreviewAppearance(),
     'isHeroTank': True,
     'previousBackAlias': previousBackAlias}), scope=EVENT_BUS_SCOPE.LOBBY)


def hideVehiclePreview():
    g_eventBus.handleEvent(events.HideWindowEvent(events.HideWindowEvent.HIDE_VEHICLE_PREVIEW), scope=EVENT_BUS_SCOPE.LOBBY)


def hideBattleResults():
    g_eventBus.handleEvent(events.HideWindowEvent(events.HideWindowEvent.HIDE_BATTLE_RESULT_WINDOW), scope=EVENT_BUS_SCOPE.LOBBY)


def hideWebBrowser(browserID=None):
    g_eventBus.handleEvent(events.HideWindowEvent(events.HideWindowEvent.HIDE_BROWSER_WINDOW, ctx={'browserID': browserID}), scope=EVENT_BUS_SCOPE.LOBBY)


def hideWebBrowserOverlay():
    g_eventBus.handleEvent(events.HideWindowEvent(events.HideWindowEvent.HIDE_OVERLAY_BROWSER_VIEW), scope=EVENT_BUS_SCOPE.LOBBY)


def showAwardWindow(award, isUniqueName=True):
    if isPopupsWindowsOpenDisabled():
        LOG_WARNING('Award popup disabled', award, isUniqueName)
        return
    if isUniqueName:
        name = getUniqueViewName(VIEW_ALIAS.AWARD_WINDOW)
    else:
        name = VIEW_ALIAS.AWARD_WINDOW
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.AWARD_WINDOW, name=name, ctx={'award': award}), EVENT_BUS_SCOPE.LOBBY)


def showModalAwardWindow(award):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.AWARD_WINDOW_MODAL, name=getUniqueViewName(VIEW_ALIAS.AWARD_WINDOW_MODAL), ctx={'award': award}), EVENT_BUS_SCOPE.LOBBY)


def showMissionAwardWindow(award):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.MISSION_AWARD_WINDOW, name=getUniqueViewName(VIEW_ALIAS.MISSION_AWARD_WINDOW), ctx={'award': award}), EVENT_BUS_SCOPE.LOBBY)


def showPersonalMissionsQuestAwardScreen(quest, ctx, proxyEvent):
    alias = PERSONAL_MISSIONS_ALIASES.PERSONAL_MISSIONS_QUEST_AWARD_SCREEN_ALIAS
    g_eventBus.handleEvent(events.LoadViewEvent(alias, name=getUniqueViewName(alias), ctx={'quest': quest,
     'ctxData': ctx,
     'proxyEvent': proxyEvent}), EVENT_BUS_SCOPE.LOBBY)


def showProfileWindow(databaseID, userName):
    alias = VIEW_ALIAS.PROFILE_WINDOW
    g_eventBus.handleEvent(events.LoadViewEvent(alias, getViewName(alias, databaseID), ctx={'userName': userName,
     'databaseID': databaseID}), EVENT_BUS_SCOPE.LOBBY)


def showClanProfileWindow(clanDbID, clanAbbrev):
    alias = CLANS_ALIASES.CLAN_PROFILE_MAIN_WINDOW_PY
    g_eventBus.handleEvent(events.LoadViewEvent(alias, getViewName(alias, clanDbID), ctx={'clanDbID': clanDbID,
     'clanAbbrev': clanAbbrev}), EVENT_BUS_SCOPE.LOBBY)


def showClanSearchWindow():
    alias = CLANS_ALIASES.CLAN_SEARCH_WINDOW_PY
    g_eventBus.handleEvent(events.LoadViewEvent(alias, alias, ctx=None), EVENT_BUS_SCOPE.LOBBY)
    return


def showClanInvitesWindow():
    g_eventBus.handleEvent(events.LoadViewEvent(CLANS_ALIASES.CLAN_PROFILE_INVITES_WINDOW_PY), EVENT_BUS_SCOPE.LOBBY)


def showClanPersonalInvitesWindow():
    g_eventBus.handleEvent(events.LoadViewEvent(CLANS_ALIASES.CLAN_PERSONAL_INVITES_WINDOW_PY), EVENT_BUS_SCOPE.LOBBY)


def showClanSendInviteWindow(clanDbID):
    alias = CLANS_ALIASES.CLAN_PROFILE_SEND_INVITES_WINDOW_PY
    g_eventBus.handleEvent(events.LoadViewEvent(alias, getViewName(alias, clanDbID), ctx={'clanDbID': clanDbID,
     'ctrlType': CTRL_ENTITY_TYPE.UNIT}), scope=EVENT_BUS_SCOPE.LOBBY)


def selectVehicleInHangar(itemCD):
    from CurrentVehicle import g_currentVehicle
    itemsCache = dependency.instance(IItemsCache)
    veh = itemsCache.items.getItemByCD(int(itemCD))
    if not veh.isInInventory:
        raise SoftException('Vehicle (itemCD={}) must be in inventory.'.format(itemCD))
    g_currentVehicle.selectVehicle(veh.invID)
    showHangar()


def showPersonalCase(tankmanInvID, tabIndex, scope=EVENT_BUS_SCOPE.DEFAULT):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.PERSONAL_CASE, getViewName(VIEW_ALIAS.PERSONAL_CASE, tankmanInvID), {'tankmanID': tankmanInvID,
     'page': tabIndex}), scope)


def showPremiumWindow(arenaUniqueID=0, premiumBonusesDiff=None):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.PREMIUM_WINDOW, getViewName(VIEW_ALIAS.PREMIUM_WINDOW), ctx={'arenaUniqueID': arenaUniqueID,
     'premiumBonusesDiff': premiumBonusesDiff}), EVENT_BUS_SCOPE.LOBBY)


def showPremiumDialog():
    if isIngameShopEnabled():
        url = getBuyPremiumUrl()
        showWebShop(url)
    else:
        g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.PREMIUM_WINDOW), EVENT_BUS_SCOPE.LOBBY)


def showBoostersWindow(tabID=None):
    if isIngameShopEnabled():
        showStorage(STORAGE_CONSTANTS.PERSONAL_RESERVES)
    else:
        ctx = {'tabID': tabID} if tabID is not None else {}
        g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.BOOSTERS_WINDOW, ctx=ctx), EVENT_BUS_SCOPE.LOBBY)
    return


@process
@dependency.replace_none_kwargs(goodiesCache=IGoodiesCache)
def showBoosterActivateDialog(boosterIntCD, goodiesCache=None):
    newBooster = goodiesCache.getBooster(boosterIntCD)
    if not newBooster.isReadyToActivate:
        return
    else:
        criteria = REQ_CRITERIA.BOOSTER.ACTIVE | REQ_CRITERIA.BOOSTER.BOOSTER_TYPES([newBooster.boosterType])
        activeBoosters = goodiesCache.getBoosters(criteria=criteria).values()
        curBooster = max(activeBoosters, key=attrgetter('effectValue')) if activeBoosters else None
        messageCtx = {'newBoosterName': text_styles.middleTitle(newBooster.description)}
        if curBooster is None:
            key = BOOSTER_CONSTANTS.BOOSTER_ACTIVATION_CONFORMATION_TEXT_KEY
        else:
            key = BOOSTER_CONSTANTS.BOOSTER_REPLACE_CONFORMATION_TEXT_KEY
            messageCtx['curBoosterName'] = text_styles.middleTitle(curBooster.description)
        shouldActivate = yield DialogsInterface.showDialog(I18nConfirmDialogMeta(key=key, messageCtx=messageCtx, focusedID=DIALOG_BUTTON_ID.CLOSE))
        if shouldActivate:
            result = yield BoosterActivator(newBooster).request()
            if result.userMsg:
                SystemMessages.pushI18nMessage(result.userMsg, type=result.sysMsgType)
        return


def stopTutorial():
    g_eventBus.handleEvent(events.TutorialEvent(events.TutorialEvent.STOP_TRAINING), scope=EVENT_BUS_SCOPE.GLOBAL)


def runTutorialChain(chapterID):
    g_eventBus.handleEvent(events.TutorialEvent(events.TutorialEvent.START_TRAINING, settingsID='TRIGGERS_CHAINS', initialChapter=chapterID, restoreIfRun=True))


def runSalesChain(chapterID):
    g_eventBus.handleEvent(events.TutorialEvent(events.TutorialEvent.START_TRAINING, settingsID='SALES_TRIGGERS', initialChapter=chapterID, restoreIfRun=True))


def changeAppResolution(width, height, scale):
    g_eventBus.handleEvent(events.GameEvent(events.GameEvent.CHANGE_APP_RESOLUTION, ctx={'width': width,
     'height': height,
     'scale': scale}), scope=EVENT_BUS_SCOPE.GLOBAL)


@process
def requestProfile(databaseID, userName, successCallback):
    itemsCache = dependency.instance(IItemsCache)
    userDossier, _, isHidden = yield itemsCache.items.requestUserDossier(databaseID)
    if userDossier is None:
        if isHidden:
            key = 'messenger/userInfoHidden'
        else:
            key = 'messenger/userInfoNotAvailable'
        DialogsInterface.showI18nInfoDialog(key, lambda result: None, I18nInfoDialogMeta(key, messageCtx={'userName': userName}))
    else:
        successCallback(databaseID, userName)
    return


def showSettingsWindow(redefinedKeyMode=False, tabIndex=None, isBattleSettings=False):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.SETTINGS_WINDOW, ctx={'redefinedKeyMode': redefinedKeyMode,
     'tabIndex': tabIndex,
     'isBattleSettings': isBattleSettings}), scope=EVENT_BUS_SCOPE.GLOBAL)


def showVehicleCompare():
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.VEHICLE_COMPARE), scope=EVENT_BUS_SCOPE.LOBBY)


@pointcutable
def showCrystalWindow():
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.CRYSTALS_PROMO_WINDOW), EVENT_BUS_SCOPE.LOBBY)


@pointcutable
def openPaymentLink():
    g_eventBus.handleEvent(events.OpenLinkEvent(events.OpenLinkEvent.PAYMENT))


@pointcutable
def showExchangeCurrencyWindow():
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.EXCHANGE_WINDOW), EVENT_BUS_SCOPE.LOBBY)


@pointcutable
def showExchangeXPWindow():
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.EXCHANGE_XP_WINDOW), EVENT_BUS_SCOPE.LOBBY)


def showBubbleTooltip(msg):
    g_eventBus.handleEvent(events.BubbleTooltipEvent(events.BubbleTooltipEvent.SHOW, msg), scope=EVENT_BUS_SCOPE.LOBBY)


@dependency.replace_none_kwargs(lobbyCtx=ILobbyContext, nyCtrl=INewYearController)
def showLootBoxEntry(lootBoxType=NewYearLootBoxes.PREMIUM, category='', lobbyCtx=None, nyCtrl=None):
    enabled = lobbyCtx.getServerSettings().isLootBoxesEnabled() and nyCtrl.isEnabled()
    if not enabled:
        from gui.impl.lobby.loot_box.loot_box_helper import showRestrictedSysMessage
        showRestrictedSysMessage()
        return
    else:
        uiLoader = dependency.instance(IGuiLoader)
        contentResId = R.views.lobby.loot_box.views.loot_box_entry_view.LootBoxEntryView()
        lootBoxEntryView = uiLoader.windowsManager.getViewByLayoutID(contentResId)
        if lootBoxEntryView is not None:
            lootBoxEntryView.destroyWindow()
        from gui.impl.lobby.loot_box.loot_box_entry_view import LootBoxEntryWindow
        window = LootBoxEntryWindow(lootBoxType, category)
        window.load()
        return


@process
@dependency.replace_none_kwargs(lobbyCtx=ILobbyContext)
def showLootBoxBuyWindow(category='', lobbyCtx=None):
    if not lobbyCtx.getServerSettings().isLootBoxesEnabled():
        _logger.error('LootBoxes are disabled on server. Nothing will be shown!')
        return
    shopConfig = lobbyCtx.getServerSettings().getLootBoxShop()
    rawUrl = shopConfig.get(NYLootBoxConsts.URL, '')
    if not rawUrl:
        _logger.error('No Loot Box Shop URL is specified. Nothing will be shown!')
        return
    source = shopConfig.get(NYLootBoxConsts.SOURCE, NYLootBoxConsts.IGB)
    url = yield URLMacros().parse(rawUrl)
    if source == NYLootBoxConsts.IGB:
        g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.LOOT_BOX_SHOP_OVERLAY, ctx={'url': url,
         'category': category}), EVENT_BUS_SCOPE.LOBBY)
    elif source == NYLootBoxConsts.EXTERNAL:
        g_eventBus.handleEvent(events.OpenLinkEvent(events.OpenLinkEvent.SPECIFIED, url))
    else:
        _logger.error('Invalid source is specified. Can not open loot box buy window!')


def showLootBoxGiftWindow():
    g_eventBus.handleEvent(events.OpenLinkEvent(events.OpenLinkEvent.LOOT_BOX_GIFT_URL))


def showLootBoxAutoOpenWindow(rewards):
    from gui.impl.lobby.loot_box.loot_box_auto_open_view import LootBoxAutoOpenWindow
    window = LootBoxAutoOpenWindow(rewards)
    window.load()


def showNYLevelUpWindow(context):
    from gui.impl.new_year.views.new_year_level_up_view import NewYearLevelUpWindow
    uiLoader = dependency.instance(IGuiLoader)
    contentResId = R.views.lobby.new_year.views.new_year_level_up_view.NewYearLevelUpView()
    levelUpView = uiLoader.windowsManager.getViewByLayoutID(contentResId)
    if levelUpView is not None and levelUpView.viewStatus == ViewStatus.LOADED:
        levelUpView.appendRewards(context)
        return
    else:
        window = NewYearLevelUpWindow(context)
        window.load()
        return


def showNyCollectionCongratsWindow(context):
    from gui.impl.new_year.views.new_year_style_reward_view import NewYearStyleRewardWindow
    uiLoader = dependency.instance(IGuiLoader)
    contentResId = R.views.lobby.loot_box.views.loot_box_special_reward_view.LootBoxSpecialRewardView()
    specialVideoResID = uiLoader.windowsManager.getViewByLayoutID(contentResId)
    if specialVideoResID is not None:
        return
    else:
        window = NewYearStyleRewardWindow(context)
        window.load()
        return


def showVideoView(videoResID, parent=None, onVideoStartHandler=None, onVideoStopHandler=None):
    from gui.impl.lobby.video_view import VideoViewWindow
    VideoViewWindow(videoResID, parent=parent, onVideoStartHandler=onVideoStartHandler, onVideoStopHandler=onVideoStopHandler).load()


def showNewYearSpecialWindow():
    from gui.impl.new_year.views.new_year_special_reward_view import NewYearSpecialRewardWindow
    window = NewYearSpecialRewardWindow()
    window.load()


def showReferralProgramWindow(url=None):
    referralController = dependency.instance(IReferralProgramController)
    if url is None:
        url = getReferralProgramURL()
    referralController.showWindow(url=url)
    return


def showTankPremiumAboutPage():
    url = GUI_SETTINGS.premiumInfo.get('baseURL')
    if url is None:
        _logger.error('premiumInfo.baseURL is missed')
    showBrowserOverlayView(url, alias=VIEW_ALIAS.OVERLAY_PREM_CONTENT_VIEW)
    return


@process
def showBrowserOverlayView(url, alias=VIEW_ALIAS.BROWSER_LOBBY_TOP_SUB, params=None, callbackOnLoad=None):
    if url:
        url = yield URLMacros().parse(url, params=params)
        g_eventBus.handleEvent(events.LoadViewEvent(alias, ctx={'url': url,
         'allowRightClick': False,
         'callbackOnLoad': callbackOnLoad}), EVENT_BUS_SCOPE.LOBBY)


def showSeniorityRewardWindow():
    from gui.impl.lobby.seniority_awards.seniority_reward_view import SeniorityRewardWindow
    uiLoader = dependency.instance(IGuiLoader)
    contentResId = R.views.lobby.seniority_awards.seniority_reward_view.SeniorityRewardView()
    if uiLoader.windowsManager.getViewByLayoutID(contentResId) is None:
        window = SeniorityRewardWindow(contentResId)
        window.load()
    return


def showProgressiveRewardWindow():
    lobbyContext = dependency.instance(ILobbyContext)
    if not lobbyContext.getServerSettings().getProgressiveRewardConfig().isEnabled:
        SystemMessages.pushMessage(backport.text(R.strings.system_messages.progressiveReward.error()), type=SystemMessages.SM_TYPE.Error)
        return
    else:
        from gui.impl.lobby.progressive_reward.progressive_reward_view import ProgressiveRewardWindow
        uiLoader = dependency.instance(IGuiLoader)
        contentResId = R.views.lobby.progressive_reward.progressive_reward_view.ProgressiveRewardView()
        if uiLoader.windowsManager.getViewByLayoutID(contentResId) is None:
            window = ProgressiveRewardWindow(contentResId)
            window.load()
        return


def showProgressiveRewardAwardWindow(bonuses, specialRewardType, currentStep):
    from gui.impl.lobby.progressive_reward.progressive_reward_award_view import ProgressiveRewardAwardWindow
    window = ProgressiveRewardAwardWindow(bonuses, specialRewardType, currentStep)
    window.load()


def showSeniorityRewardAwardWindow(qID, data):
    from gui.impl.lobby.seniority_awards.seniority_reward_award_view import SeniorityRewardAwardWindow
    window = SeniorityRewardAwardWindow(qID, data)
    window.load()


def showStylePreview(vehCD, style, styleDescr, backCallback, destoryCallback=None, backBtnDescrLabel=''):
    g_eventBus.handleEvent(events.LoadViewEvent(VIEW_ALIAS.STYLE_PREVIEW, ctx={'itemCD': vehCD,
     'style': style,
     'styleDescr': styleDescr,
     'backCallback': backCallback,
     'destroyCallback': destoryCallback,
     'backBtnDescrLabel': backBtnDescrLabel}), scope=EVENT_BUS_SCOPE.LOBBY)


@async
def showFrontlineExchangePrestigePoints(ctx):
    from gui.impl.dialogs.builders import InfoDialogBuilder
    from gui.impl.dialogs import dialogs
    from gui.impl.wrappers.user_format_string_arg_model import UserFormatStringArgModel as FmtArgs
    from gui.Scaleform.daapi.view.lobby.epicBattle.epic_helpers import exchangePrestigePoints
    from gui.server_events.formatters import formatGoldPrice, formatCrystalPrice
    from gui.game_control.epic_meta_game_ctrl import FRONTLINE_SCREENS
    __ctrl = dependency.instance(IEpicBattleMetaGameController)
    prestigePoints = ctx.get('prestige_points', 0)
    gold = ctx.get('gold', 1) * prestigePoints
    crystals = ctx.get('crystal', 1) * prestigePoints
    canBuyVehs = ctx.get('canBuy')
    if canBuyVehs:
        dialogParams = R.strings.dialogs.frontline.dialogPrestigePointsConvert
    else:
        dialogParams = R.strings.dialogs.frontline.dialogPrestigePointsConvert.haveAllTank
    builder = InfoDialogBuilder()
    builder.setMessagesAndButtons(dialogParams)
    builder.setMessageArgs(fmtArgs=[FmtArgs(str(prestigePoints), 'points', R.styles.NeutralTextStyle()), FmtArgs(formatGoldPrice(gold), 'gold', R.styles.GoldTextStyle()), FmtArgs(formatCrystalPrice(crystals), 'bons', R.styles.CrystalTextStyle())])
    result = yield await(dialogs.showSimple(builder.build()))
    if result:
        exchangePrestigePoints()
    __ctrl.showCustomScreen(FRONTLINE_SCREENS.REWARDS_SCREEN)


def showNewYearMainView(loadingViewParams=None, *args, **kwargs):
    from gui.impl.new_year.views.new_year_main_view import NewYearMainView
    uiLoader = dependency.instance(IGuiLoader)
    contentResId = R.views.lobby.new_year.views.new_year_main_view.NewYearMainView()
    newYearView = uiLoader.windowsManager.getViewByLayoutID(contentResId)
    if newYearView is not None:
        newYearView.switchView(loadingViewParams, *args, **kwargs)
    else:
        g_eventBus.handleEvent(events.LoadUnboundViewEvent(contentResId, NewYearMainView, ScopeTemplates.LOBBY_SUB_SCOPE, loadingViewParams=loadingViewParams, *args, **kwargs), scope=EVENT_BUS_SCOPE.LOBBY)
    return


def showNewYearVehiclesView(*args, **kwargs):
    from gui.impl.new_year.views.new_year_vehicles_view import NewYearVehiclesView
    contentResId = R.views.lobby.new_year.views.new_year_vehicles_view.NewYearVehiclesView()
    g_eventBus.handleEvent(events.LoadUnboundViewEvent(contentResId, NewYearVehiclesView, ScopeTemplates.LOBBY_SUB_SCOPE, *args, **kwargs), scope=EVENT_BUS_SCOPE.LOBBY)


def showNewYearInfoPage():
    url = GUI_SETTINGS.newYearInfo.get('baseURL')
    if url is None:
        _logger.error('newYearInfo.baseURL is missed')
    showBrowserOverlayView(url, alias=VIEW_ALIAS.OVERLAY_PREM_CONTENT_VIEW)
    return
