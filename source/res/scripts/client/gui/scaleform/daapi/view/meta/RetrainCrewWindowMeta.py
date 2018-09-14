# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/Scaleform/daapi/view/meta/RetrainCrewWindowMeta.py
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView

class RetrainCrewWindowMeta(AbstractWindowView):
    """
    DO NOT MODIFY!
    Generated with yaml.
    __author__ = 'yaml_processor'
    @extends AbstractWindowView
    """

    def submit(self, operationId):
        self._printOverrideError('submit')

    def changeRetrainType(self, retrainTypeIndex):
        self._printOverrideError('changeRetrainType')

    def as_setCrewDataS(self, data):
        """
        :param data: Represented by RetrainCrewBlockVO (AS)
        """
        return self.flashObject.as_setCrewData(data) if self._isDAAPIInited() else None

    def as_setVehicleDataS(self, data):
        """
        :param data: Represented by RetrainVehicleBlockVO (AS)
        """
        return self.flashObject.as_setVehicleData(data) if self._isDAAPIInited() else None

    def as_setCrewOperationDataS(self, data):
        """
        :param data: Represented by RetrainCrewOperationVO (AS)
        """
        return self.flashObject.as_setCrewOperationData(data) if self._isDAAPIInited() else None

    def as_setAllCrewDataS(self, data):
        """
        :param data: Represented by RetrainCrewBlockVOBase (AS)
        """
        return self.flashObject.as_setAllCrewData(data) if self._isDAAPIInited() else None
