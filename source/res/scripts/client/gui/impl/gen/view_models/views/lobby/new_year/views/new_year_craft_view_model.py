# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/impl/gen/view_models/views/lobby/new_year/views/new_year_craft_view_model.py
from frameworks.wulf import ViewModel
from gui.impl.gen.view_models.ui_kit.list_model import ListModel
from gui.impl.gen.view_models.views.lobby.new_year.components.ny_craft.ny_craft_antiduplicator_model import NyCraftAntiduplicatorModel
from gui.impl.gen.view_models.views.lobby.new_year.components.ny_craft.ny_craft_mega_device_model import NyCraftMegaDeviceModel
from gui.impl.gen.view_models.views.lobby.new_year.components.ny_craft.ny_craft_monitor_model import NyCraftMonitorModel
from gui.impl.gen.view_models.views.lobby.new_year.components.ny_craft.ny_craft_regular_config_model import NyCraftRegularConfigModel

class NewYearCraftViewModel(ViewModel):
    __slots__ = ('onCraftBtnClick', 'onAddCraftDecoration')

    def __init__(self, properties=11, commands=2):
        super(NewYearCraftViewModel, self).__init__(properties=properties, commands=commands)

    @property
    def craftCarousel(self):
        return self._getViewModel(0)

    @property
    def regularConfig(self):
        return self._getViewModel(1)

    @property
    def megaDevice(self):
        return self._getViewModel(2)

    @property
    def antiduplicator(self):
        return self._getViewModel(3)

    @property
    def monitor(self):
        return self._getViewModel(4)

    def getEnableCraftBtn(self):
        return self._getBool(5)

    def setEnableCraftBtn(self, value):
        self._setBool(5, value)

    def getCraftPrice(self):
        return self._getNumber(6)

    def setCraftPrice(self, value):
        self._setNumber(6, value)

    def getCraftIcon(self):
        return self._getString(7)

    def setCraftIcon(self, value):
        self._setString(7, value)

    def getIsCrafting(self):
        return self._getBool(8)

    def setIsCrafting(self, value):
        self._setBool(8, value)

    def getCraftState(self):
        return self._getNumber(9)

    def setCraftState(self, value):
        self._setNumber(9, value)

    def getIsRuUserLanguage(self):
        return self._getBool(10)

    def setIsRuUserLanguage(self, value):
        self._setBool(10, value)

    def _initialize(self):
        super(NewYearCraftViewModel, self)._initialize()
        self._addViewModelProperty('craftCarousel', ListModel())
        self._addViewModelProperty('regularConfig', NyCraftRegularConfigModel())
        self._addViewModelProperty('megaDevice', NyCraftMegaDeviceModel())
        self._addViewModelProperty('antiduplicator', NyCraftAntiduplicatorModel())
        self._addViewModelProperty('monitor', NyCraftMonitorModel())
        self._addBoolProperty('enableCraftBtn', False)
        self._addNumberProperty('craftPrice', 0)
        self._addStringProperty('craftIcon', '')
        self._addBoolProperty('isCrafting', False)
        self._addNumberProperty('craftState', -1)
        self._addBoolProperty('isRuUserLanguage', True)
        self.onCraftBtnClick = self._addCommand('onCraftBtnClick')
        self.onAddCraftDecoration = self._addCommand('onAddCraftDecoration')
