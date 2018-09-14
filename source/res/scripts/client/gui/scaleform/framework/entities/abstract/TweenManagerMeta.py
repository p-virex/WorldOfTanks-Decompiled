# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/Scaleform/framework/entities/abstract/TweenManagerMeta.py
from gui.Scaleform.framework.entities.BaseDAAPIModule import BaseDAAPIModule

class TweenManagerMeta(BaseDAAPIModule):
    """
    DO NOT MODIFY!
    Generated with yaml.
    __author__ = 'yaml_processor'
    @extends BaseDAAPIModule
    """

    def createTween(self, tween):
        """
        :param tween: Represented by ITween (AS)
        """
        self._printOverrideError('createTween')

    def disposeTween(self, tween):
        """
        :param tween: Represented by ITween (AS)
        """
        self._printOverrideError('disposeTween')

    def disposeAll(self):
        self._printOverrideError('disposeAll')

    def as_setDataFromXmlS(self, data):
        """
        :param data: Represented by TweenConstraintsVO (AS)
        """
        return self.flashObject.as_setDataFromXml(data) if self._isDAAPIInited() else None
