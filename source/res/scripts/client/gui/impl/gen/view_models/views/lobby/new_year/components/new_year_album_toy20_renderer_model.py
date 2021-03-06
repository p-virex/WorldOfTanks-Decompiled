# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/impl/gen/view_models/views/lobby/new_year/components/new_year_album_toy20_renderer_model.py
from gui.impl.gen.view_models.views.lobby.new_year.components.new_year_album_toy_renderer_model import NewYearAlbumToyRendererModel

class NewYearAlbumToy20RendererModel(NewYearAlbumToyRendererModel):
    __slots__ = ()

    def __init__(self, properties=11, commands=0):
        super(NewYearAlbumToy20RendererModel, self).__init__(properties=properties, commands=commands)

    def getIsMega(self):
        return self._getBool(6)

    def setIsMega(self, value):
        self._setBool(6, value)

    def getBonusValue(self):
        return self._getReal(7)

    def setBonusValue(self, value):
        self._setReal(7, value)

    def getIsInInventory(self):
        return self._getBool(8)

    def setIsInInventory(self, value):
        self._setBool(8, value)

    def getNewNumber(self):
        return self._getNumber(9)

    def setNewNumber(self, value):
        self._setNumber(9, value)

    def getToyType(self):
        return self._getString(10)

    def setToyType(self, value):
        self._setString(10, value)

    def _initialize(self):
        super(NewYearAlbumToy20RendererModel, self)._initialize()
        self._addBoolProperty('isMega', False)
        self._addRealProperty('bonusValue', 0.0)
        self._addBoolProperty('isInInventory', False)
        self._addNumberProperty('newNumber', 0)
        self._addStringProperty('toyType', '')
