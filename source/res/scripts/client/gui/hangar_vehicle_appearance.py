# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/hangar_vehicle_appearance.py
import weakref
import math
from collections import namedtuple
import BigWorld
import Event
import Math
import VehicleStickers
import Vehicular
import math_utils
from debug_utils import LOG_ERROR
from dossiers2.ui.achievements import MARK_ON_GUN_RECORD
from gui import g_tankActiveCamouflage
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.customization.outfit import Area, REGIONS_BY_SLOT_TYPE
from gui.shared.gui_items.customization.slots import ANCHOR_TYPE_TO_SLOT_TYPE_MAP, SLOT_ASPECT_RATIO, SLOT_TYPES, BaseCustomizationSlot, EmblemSlot, getProgectionDecalAspect
from gui.shared.items_cache import CACHE_SYNC_REASON
from helpers import dependency
from items.components.c11n_constants import ApplyArea, SeasonType
from skeletons.account_helpers.settings_core import ISettingsCore
from skeletons.gui.shared import IItemsCache
from skeletons.gui.shared.gui_items import IGuiItemsFactory
from vehicle_systems import camouflages
from vehicle_systems.components.vehicle_shadow_manager import VehicleShadowManager
from vehicle_systems.tankStructure import ModelsSetParams, TankPartNames, ColliderTypes, TankPartIndexes
from vehicle_systems.tankStructure import VehiclePartsTuple, TankNodeNames
from svarog_script.script_game_object import ComponentDescriptor, ScriptGameObject
from vehicle_systems.stricted_loading import makeCallbackWeak
from CurrentVehicle import g_currentVehicle, g_currentPreviewVehicle
from gui.hangar_cameras.hangar_camera_common import CameraMovementStates, CameraRelatedEvents
from gui.shared import g_eventBus, EVENT_BUS_SCOPE
from gui.ClientHangarSpace import hangarCFG
from gui.battle_control.vehicle_getter import hasTurretRotator
_SHOULD_CHECK_DECAL_UNDER_GUN = True
_PROJECTION_DECAL_OVERLAPPING_FACTOR = 0.7
_HANGAR_TURRET_SHIFT = math.pi / 8
AnchorLocation = namedtuple('AnchorLocation', ['position', 'normal', 'up'])
AnchorId = namedtuple('AnchorId', ('slotType', 'areaId', 'regionIdx'))
AnchorHelper = namedtuple('AnchorHelper', ['location',
 'descriptor',
 'turretYaw',
 'partIdx',
 'attachedPartIdx'])
AnchorParams = namedtuple('AnchorParams', ['location', 'descriptor', 'id'])
_DEFAULT_TURRET_YAW_ANGLE = 0.0
_DEFAULT_GUN_PITCH_ANGLE = 0.0

class _LoadStateNotifier(object):
    __em = Event.EventManager()

    def __init__(self, loaded=False):
        self._onLoaded = Event.Event(self.__em)
        self._onUnloaded = Event.Event(self.__em)
        self.__loaded = loaded

    def destroy(self):
        self.__em.clear()

    @property
    def isLoaded(self):
        return self.__loaded

    def subscribe(self, onLoadCallback, onUnloadCallback):
        self._onLoaded += onLoadCallback
        self._onUnloaded += onUnloadCallback

    def unsubscribe(self, onLoadCallback, onUnloadCallback):
        self._onLoaded -= onLoadCallback
        self._onUnloaded -= onUnloadCallback

    def load(self):
        self.__loaded = True
        BigWorld.callback(0.0, makeCallbackWeak(self._onLoaded))

    def unload(self):
        self.__loaded = False
        self._onUnloaded()


class HangarVehicleAppearance(ScriptGameObject):
    __ROOT_NODE_NAME = 'V'
    itemsCache = dependency.descriptor(IItemsCache)
    itemsFactory = dependency.descriptor(IGuiItemsFactory)
    settingsCore = dependency.descriptor(ISettingsCore)
    wheelsAnimator = ComponentDescriptor()
    trackNodesAnimator = ComponentDescriptor()
    collisions = ComponentDescriptor()
    shadowManager = ComponentDescriptor()
    dirtComponent = ComponentDescriptor()
    c11nComponent = ComponentDescriptor()
    tracks = ComponentDescriptor()
    collisionObstaclesCollector = ComponentDescriptor()
    tessellationCollisionSensor = ComponentDescriptor()

    @property
    def compoundModel(self):
        return self.__vEntity.model if self.__vEntity else None

    @property
    def id(self):
        return self.__vEntity.id

    fashion = property(lambda self: self.__fashions[0])

    @property
    def filter(self):
        return None

    def __init__(self, spaceId, vEntity):
        ScriptGameObject.__init__(self, vEntity.spaceID)
        self.__loadState = _LoadStateNotifier()
        self.__curBuildInd = 0
        self.__vDesc = None
        self.__vState = None
        size = len(TankPartNames.ALL)
        self.__fashions = VehiclePartsTuple(*([None] * size))
        self.__repaintHandlers = [None] * size
        self.__camoHandlers = [None] * size
        self.__projectionDecalsHandlers = [None] * size
        self.__projectionDecalsUpdater = None
        self.__spaceId = spaceId
        self.__vEntity = weakref.proxy(vEntity)
        self.__onLoadedCallback = None
        self.__onLoadedAfterRefreshCallback = None
        self.__vehicleStickers = None
        self.__isVehicleDestroyed = False
        self.__outfit = None
        self.__staticTurretYaw = 0.0
        self.__staticGunPitch = 0.0
        self.__anchorsHelpers = None
        self.__anchorsParams = None
        self.__modelAnimators = []
        self.shadowManager = None
        cfg = hangarCFG()
        self.__currentEmblemsAlpha = cfg['emblems_alpha_undamaged']
        self.__showMarksOnGun = self.settingsCore.getSetting('showMarksOnGun')
        self.settingsCore.onSettingsChanged += self.__onSettingsChanged
        self.itemsCache.onSyncCompleted += self.__onItemsCacheSyncCompleted
        g_eventBus.addListener(CameraRelatedEvents.CAMERA_ENTITY_UPDATED, self.__handleEntityUpdated)
        g_currentVehicle.onChanged += self.__onVehicleChanged
        return

    def recreate(self, vDesc, vState=None, callback=None, outfit=None):
        self.__onLoadedCallback = callback
        self.__reload(vDesc, vState or self.__vState, outfit or self._getActiveOutfit())

    def remove(self):
        self.__clearModelAnimators()
        self.__loadState.unload()
        self.__vDesc = None
        self.__vState = None
        self.__isVehicleDestroyed = False
        self.__vEntity.model = None
        if self.shadowManager is not None:
            self.shadowManager.updatePlayerTarget(None)
        if self.collisions:
            BigWorld.removeCameraCollider(self.collisions.getColliderID())
            self.collisions = None
        return

    def refresh(self, outfit=None, callback=None):
        if self.__loadState.isLoaded and self.__vDesc:
            if callback is not None:
                self.__onLoadedAfterRefreshCallback = callback
            self.__reload(self.__vDesc, self.__vState, outfit or self.__outfit)
        return

    def destroy(self):
        if self.fashion is not None:
            self.fashion.removePhysicalTracks()
        if self.shadowManager is not None:
            self.shadowManager.updatePlayerTarget(None)
        ScriptGameObject.deactivate(self)
        ScriptGameObject.destroy(self)
        self.__clearModelAnimators()
        self.__vDesc = None
        self.__vState = None
        self.__loadState.unload()
        self.__loadState.destroy()
        self.__loadState = None
        self.__curBuildInd = 0
        self.__vEntity = None
        self.__onLoadedCallback = None
        self.__onLoadedAfterRefreshCallback = None
        self.settingsCore.onSettingsChanged -= self.__onSettingsChanged
        self.itemsCache.onSyncCompleted -= self.__onItemsCacheSyncCompleted
        g_eventBus.removeListener(CameraRelatedEvents.CAMERA_ENTITY_UPDATED, self.__handleEntityUpdated)
        g_currentVehicle.onChanged -= self.__onVehicleChanged
        return

    @property
    def loadState(self):
        return self.__loadState

    @property
    def fakeShadowDefinedInHullTexture(self):
        return self.__vDesc.hull.hangarShadowTexture if self.__vDesc else None

    def isLoaded(self):
        return self.__loadState.isLoaded

    def recreateRequired(self, newOutfit):
        shouldUpdateModelsSet = self.__outfit.modelsSet != newOutfit.modelsSet
        shouldUpdateAttachments = not self.__outfit.attachments.isEqual(newOutfit.attachments)
        return shouldUpdateModelsSet or shouldUpdateAttachments

    def computeVehicleHeight(self):
        gunLength = 0.0
        height = 0.0
        if self.collisions is not None:
            desc = self.__vDesc
            hullBB = self.collisions.getBoundingBox(TankPartNames.getIdx(TankPartNames.HULL))
            turretBB = self.collisions.getBoundingBox(TankPartNames.getIdx(TankPartNames.TURRET))
            gunBB = self.collisions.getBoundingBox(TankPartNames.getIdx(TankPartNames.GUN))
            hullTopY = desc.chassis.hullPosition[1] + hullBB[1][1]
            turretTopY = desc.chassis.hullPosition[1] + desc.hull.turretPositions[0][1] + turretBB[1][1]
            gunTopY = desc.chassis.hullPosition[1] + desc.hull.turretPositions[0][1] + desc.turret.gunPosition[1] + gunBB[1][1]
            gunLength = math.fabs(gunBB[1][2] - gunBB[0][2])
            height = max(hullTopY, max(turretTopY, gunTopY))
        return (height, gunLength)

    def computeVehicleLength(self):
        vehicleLength = 0.0
        if self.collisions is not None:
            hullBB = self.collisions.getBoundingBox(TankPartNames.getIdx(TankPartNames.HULL))
            vehicleLength = abs(hullBB[1][2] - hullBB[0][2])
        return vehicleLength

    def computeFullVehicleLength(self):
        hullBB = Math.Matrix(self.__vEntity.model.getBoundsForPart(TankPartIndexes.HULL))
        return hullBB.applyVector(Math.Vector3(0.0, 0.0, 1.0)).length

    def __reload(self, vDesc, vState, outfit):
        self.__loadState.unload()
        if self.fashion is not None:
            self.fashion.removePhysicalTracks()
        ScriptGameObject.deactivate(self)
        self.tracks = None
        self.collisionObstaclesCollector = None
        self.tessellationCollisionSensor = None
        self.shadowManager = VehicleShadowManager()
        self.shadowManager.updatePlayerTarget(None)
        self.__outfit = outfit
        self.__startBuild(vDesc, vState)
        return

    def __startBuild(self, vDesc, vState):
        self.__curBuildInd += 1
        self.__vState = vState
        self.__resources = {}
        self.__vehicleStickers = None
        cfg = hangarCFG()
        if vState == 'undamaged':
            self.__currentEmblemsAlpha = cfg['emblems_alpha_undamaged']
            self.__isVehicleDestroyed = False
        else:
            self.__currentEmblemsAlpha = cfg['emblems_alpha_damaged']
            self.__isVehicleDestroyed = True
        self.__vDesc = vDesc
        resources = camouflages.getCamoPrereqs(self.__outfit, vDesc)
        attachments = camouflages.getAttachments(self.__outfit, vDesc)
        modelsSet = self.__outfit.modelsSet
        splineDesc = vDesc.chassis.splineDesc
        if splineDesc is not None:
            resources.append(splineDesc.segmentModelLeft(modelsSet))
            resources.append(splineDesc.segmentModelRight(modelsSet))
            if splineDesc.leftDesc is not None:
                resources.append(splineDesc.leftDesc)
            if splineDesc.rightDesc is not None:
                resources.append(splineDesc.rightDesc)
            segment2ModelLeft = splineDesc.segment2ModelLeft(modelsSet)
            if segment2ModelLeft is not None:
                resources.append(segment2ModelLeft)
            segment2ModelRight = splineDesc.segment2ModelRight(modelsSet)
            if segment2ModelRight is not None:
                resources.append(segment2ModelRight)
        from vehicle_systems import model_assembler
        resources.append(model_assembler.prepareCompoundAssembler(self.__vDesc, ModelsSetParams(modelsSet, self.__vState, attachments), self.__spaceId))
        g_eventBus.handleEvent(CameraRelatedEvents(CameraRelatedEvents.VEHICLE_LOADING, ctx={'started': True,
         'vEntityId': self.__vEntity.id}), scope=EVENT_BUS_SCOPE.DEFAULT)
        cfg = hangarCFG()
        gunScale = Math.Vector3(1.0, 1.0, 1.1)
        capsuleScale = Math.Vector3(1.5, 1.5, 1.5)
        loadedGunScale = cfg.get('cam_capsule_gun_scale', gunScale)
        if loadedGunScale is not None:
            gunScale = loadedGunScale
        loadedCapsuleScale = cfg.get('cam_capsule_scale', capsuleScale)
        if loadedCapsuleScale is not None:
            capsuleScale = loadedCapsuleScale
        bspModels = ((TankPartNames.getIdx(TankPartNames.CHASSIS), vDesc.chassis.hitTester.bspModelName),
         (TankPartNames.getIdx(TankPartNames.HULL), vDesc.hull.hitTester.bspModelName),
         (TankPartNames.getIdx(TankPartNames.TURRET), vDesc.turret.hitTester.bspModelName),
         (TankPartNames.getIdx(TankPartNames.GUN), vDesc.gun.hitTester.bspModelName),
         (TankPartNames.getIdx(TankPartNames.GUN) + 1, vDesc.hull.hitTester.bspModelName, capsuleScale),
         (TankPartNames.getIdx(TankPartNames.GUN) + 2, vDesc.turret.hitTester.bspModelName, capsuleScale),
         (TankPartNames.getIdx(TankPartNames.GUN) + 3, vDesc.gun.hitTester.bspModelName, gunScale))
        collisionAssembler = BigWorld.CollisionAssembler(bspModels, self.__spaceId)
        resources.append(collisionAssembler)
        physicalTracksBuilders = vDesc.chassis.physicalTracks
        for name, builders in physicalTracksBuilders.iteritems():
            for index, builder in enumerate(builders):
                resources.append(builder.createLoader(self.__spaceId, '{0}{1}PhysicalTrack'.format(name, index), modelsSet))

        BigWorld.loadResourceListBG(tuple(resources), makeCallbackWeak(self.__onResourcesLoaded, self.__curBuildInd))
        return

    def __onResourcesLoaded(self, buildInd, resourceRefs):
        if not self.__vDesc:
            return
        if buildInd != self.__curBuildInd:
            return
        failedIDs = resourceRefs.failedIDs
        resources = self.__resources
        succesLoaded = True
        for resID, resource in resourceRefs.items():
            if resID not in failedIDs:
                resources[resID] = resource
            LOG_ERROR('Could not load %s' % resID)
            succesLoaded = False

        if self.collisions:
            BigWorld.removeCameraCollider(self.collisions.getColliderID())
        self.collisions = resourceRefs['collisionAssembler']
        if succesLoaded:
            self.__setupModel(buildInd)
        g_eventBus.handleEvent(CameraRelatedEvents(CameraRelatedEvents.VEHICLE_LOADING, ctx={'started': False,
         'vEntityId': self.__vEntity.id}), scope=EVENT_BUS_SCOPE.DEFAULT)
        super(HangarVehicleAppearance, self).activate()

    def __onAnimatorsLoaded(self, buildInd, outfit, resourceRefs):
        if not self.__vDesc:
            return
        if buildInd != self.__curBuildInd:
            return
        self.__clearModelAnimators()
        self.__modelAnimators = camouflages.getModelAnimators(outfit, self.__vDesc, self.__spaceId, resourceRefs, self.compoundModel)
        for animator in self.__modelAnimators:
            animator.start()

    def __onSettingsChanged(self, diff):
        if 'showMarksOnGun' in diff:
            self.__showMarksOnGun = not diff['showMarksOnGun']
            self.refresh()

    def _getActiveOutfit(self):
        if g_currentPreviewVehicle.isPresent() and not g_currentPreviewVehicle.isHeroTank or not g_currentVehicle.isPresent():
            return self.itemsFactory.createOutfit()
        else:
            vehicle = g_currentVehicle.item
            if not vehicle:
                return
            nyOutfit = vehicle.getNewYearOutfit()
            if nyOutfit is not None:
                return nyOutfit
            season = g_tankActiveCamouflage.get(vehicle.intCD, SeasonType.UNDEFINED)
            if season == SeasonType.UNDEFINED:
                season = vehicle.getAnyOutfitSeason()
            g_tankActiveCamouflage[vehicle.intCD] = season
            outfit = vehicle.getOutfit(season)
            if not outfit:
                outfit = self.itemsFactory.createOutfit()
            return outfit

    def __assembleModel(self):
        from vehicle_systems import model_assembler
        resources = self.__resources
        self.__vEntity.model = resources[self.__vDesc.name]
        if not self.__isVehicleDestroyed:
            self.__fashions = VehiclePartsTuple(BigWorld.WGVehicleFashion(), BigWorld.WGBaseFashion(), BigWorld.WGBaseFashion(), BigWorld.WGBaseFashion())
            model_assembler.setupTracksFashion(self.__vDesc, self.__fashions.chassis)
            self.__vEntity.model.setupFashions(self.__fashions)
            model_assembler.assembleCollisionObstaclesCollector(self, None, self.__vDesc, BigWorld.player().spaceID)
            model_assembler.assembleTessellationCollisionSensor(self, None)
            wheelsScroll = None
            wheelsSteering = None
            if self.__vDesc.chassis.generalWheelsAnimatorConfig is not None:
                scrollableWheelsCount = self.__vDesc.chassis.generalWheelsAnimatorConfig.getWheelsCount()
                wheelsScroll = [ (lambda : 0.0) for _ in xrange(scrollableWheelsCount) ]
                steerableWheelsCount = self.__vDesc.chassis.generalWheelsAnimatorConfig.getSteerableWheelsCount()
                wheelsSteering = [ (lambda : 0.0) for _ in xrange(steerableWheelsCount) ]
            chassisFashion = self.__fashions.chassis
            splineTracksImpl = model_assembler.setupSplineTracks(chassisFashion, self.__vDesc, self.__vEntity.model, self.__resources, self.__outfit.modelsSet)
            self.wheelsAnimator = model_assembler.createWheelsAnimator(self, ColliderTypes.VEHICLE_COLLIDER, self.__vDesc, lambda : 0, wheelsScroll, wheelsSteering, splineTracksImpl)
            self.trackNodesAnimator = model_assembler.createTrackNodesAnimator(self, self.__vDesc)
            model_assembler.assembleTracks(self.__resources, self.__vDesc, self, splineTracksImpl, True)
            dirtEnabled = BigWorld.WG_dirtEnabled() and 'HD' in self.__vDesc.type.tags
            if dirtEnabled:
                dirtHandlers = [BigWorld.PyDirtHandler(True, self.__vEntity.model.node(TankPartNames.CHASSIS).position.y),
                 BigWorld.PyDirtHandler(False, self.__vEntity.model.node(TankPartNames.HULL).position.y),
                 BigWorld.PyDirtHandler(False, self.__vEntity.model.node(TankPartNames.TURRET).position.y),
                 BigWorld.PyDirtHandler(False, self.__vEntity.model.node(TankPartNames.GUN).position.y)]
                modelHeight, _ = self.computeVehicleHeight()
                self.dirtComponent = self.createComponent(Vehicular.DirtComponent, dirtHandlers, modelHeight)
                for fashionIdx, _ in enumerate(TankPartNames.ALL):
                    self.__fashions[fashionIdx].addMaterialHandler(dirtHandlers[fashionIdx])

                self.dirtComponent.setBase()
            outfitData = camouflages.getOutfitData(self, self.__outfit, self.__vDesc, self.__vState != 'undamaged')
            self.c11nComponent = self.createComponent(Vehicular.C11nEditComponent, self.__fashions, self.compoundModel, outfitData)
            self.__updateDecals(self.__outfit)
            self.__updateSequences(self.__outfit)
        else:
            self.__fashions = VehiclePartsTuple(BigWorld.WGVehicleFashion(), BigWorld.WGBaseFashion(), BigWorld.WGBaseFashion(), BigWorld.WGBaseFashion())
            self.__vEntity.model.setupFashions(self.__fashions)
            self.wheelsAnimator = None
            self.trackNodesAnimator = None
            self.dirtComponent = None
        cfg = hangarCFG()
        self.__staticTurretYaw = self.__vDesc.gun.staticTurretYaw
        self.__staticGunPitch = self.__vDesc.gun.staticPitch
        if not ('AT-SPG' in self.__vDesc.type.tags or 'SPG' in self.__vDesc.type.tags):
            if self.__staticTurretYaw is None:
                self.__staticTurretYaw = cfg['vehicle_turret_yaw']
                turretYawLimits = self.__vDesc.gun.turretYawLimits
                if turretYawLimits is not None:
                    self.__staticTurretYaw = math_utils.clamp(turretYawLimits[0], turretYawLimits[1], self.__staticTurretYaw)
            if self.__staticGunPitch is None:
                self.__staticGunPitch = cfg['vehicle_gun_pitch']
                gunPitchLimits = self.__vDesc.gun.pitchLimits['absolute']
                self.__staticGunPitch = math_utils.clamp(gunPitchLimits[0], gunPitchLimits[1], self.__staticGunPitch)
        else:
            if self.__staticTurretYaw is None:
                self.__staticTurretYaw = 0.0
            if self.__staticGunPitch is None:
                self.__staticGunPitch = 0.0
        turretYawMatrix = math_utils.createRotationMatrix((self.__staticTurretYaw, 0.0, 0.0))
        self.__vEntity.model.node(TankPartNames.TURRET, turretYawMatrix)
        gunPitchMatrix = math_utils.createRotationMatrix((0.0, self.__staticGunPitch, 0.0))
        self.__setGunMatrix(gunPitchMatrix)
        return

    def __onItemsCacheSyncCompleted(self, updateReason, _):
        if updateReason == CACHE_SYNC_REASON.DOSSIER_RESYNC and self.__vehicleStickers is not None and self.__getThisVehicleDossierInsigniaRank() != self.__vehicleStickers.getCurrentInsigniaRank():
            self.refresh()
        return

    def __getThisVehicleDossierInsigniaRank(self):
        if self.__vDesc:
            vehicleDossier = self.itemsCache.items.getVehicleDossier(self.__vDesc.type.compactDescr)
            return vehicleDossier.getRandomStats().getAchievement(MARK_ON_GUN_RECORD).getValue()

    def __setupEmblems(self, outfit):
        if self.__vehicleStickers is not None:
            self.__vehicleStickers.detach()
        insigniaRank = 0
        if self.__showMarksOnGun:
            insigniaRank = self.__getThisVehicleDossierInsigniaRank()
        self.__vehicleStickers = VehicleStickers.VehicleStickers(self.__vDesc, insigniaRank, outfit)
        self.__vehicleStickers.alpha = self.__currentEmblemsAlpha
        self.__vehicleStickers.attach(self.__vEntity.model, self.__isVehicleDestroyed, False)
        BigWorld.player().stats.get('clanDBID', self.__onClanDBIDRetrieved)
        return

    def __onClanDBIDRetrieved(self, _, clanID):
        self.__vehicleStickers.setClanID(clanID)

    def __setupModel(self, buildIdx):
        self.__assembleModel()
        cfg = hangarCFG()
        matrix = math_utils.createSRTMatrix(Math.Vector3(cfg['v_scale'], cfg['v_scale'], cfg['v_scale']), Math.Vector3(self.__vEntity.yaw, self.__vEntity.pitch, self.__vEntity.roll), self.__vEntity.position)
        self.__vEntity.model.matrix = matrix
        self.__doFinalSetup(buildIdx)
        self.__vEntity.typeDescriptor = self.__vDesc
        gunColBox = self.collisions.getBoundingBox(TankPartNames.getIdx(TankPartNames.GUN) + 3)
        center = 0.5 * (gunColBox[1] - gunColBox[0])
        gunoffset = Math.Matrix()
        gunoffset.setTranslate((0.0, 0.0, center.z + gunColBox[0].z))
        gunLink = math_utils.MatrixProviders.product(gunoffset, self.__vEntity.model.node(TankPartNames.GUN))
        collisionData = ((TankPartNames.getIdx(TankPartNames.CHASSIS), self.__vEntity.model.matrix),
         (TankPartNames.getIdx(TankPartNames.HULL), self.__vEntity.model.node(TankPartNames.HULL)),
         (TankPartNames.getIdx(TankPartNames.TURRET), self.__vEntity.model.node(TankPartNames.TURRET)),
         (TankPartNames.getIdx(TankPartNames.GUN), self.__vEntity.model.node(TankPartNames.GUN)))
        self.collisions.connect(self.__vEntity.id, ColliderTypes.VEHICLE_COLLIDER, collisionData)
        collisionData = ((TankPartNames.getIdx(TankPartNames.GUN) + 1, self.__vEntity.model.node(TankPartNames.HULL)), (TankPartNames.getIdx(TankPartNames.GUN) + 2, self.__vEntity.model.node(TankPartNames.TURRET)), (TankPartNames.getIdx(TankPartNames.GUN) + 3, gunLink))
        self.collisions.connect(self.__vEntity.id, ColliderTypes.HANGAR_VEHICLE_COLLIDER, collisionData)
        self.__reloadColliderType(self.__vEntity.state)
        self.__reloadShadowManagerTarget(self.__vEntity.state)

    def __handleEntityUpdated(self, event):
        ctx = event.ctx
        if ctx['entityId'] == self.__vEntity.id:
            self.__reloadColliderType(ctx['state'])
            self.__reloadShadowManagerTarget(ctx['state'])

    def __reloadColliderType(self, state):
        if not self.collisions:
            return
        if state != CameraMovementStates.FROM_OBJECT:
            colliderData = (self.collisions.getColliderID(), (TankPartNames.getIdx(TankPartNames.GUN) + 1, TankPartNames.getIdx(TankPartNames.GUN) + 2, TankPartNames.getIdx(TankPartNames.GUN) + 3))
            BigWorld.appendCameraCollider(colliderData)
        else:
            BigWorld.removeCameraCollider(self.collisions.getColliderID())

    def __reloadShadowManagerTarget(self, state):
        if not self.shadowManager or not self.__vEntity.model:
            return
        else:
            if state == CameraMovementStates.ON_OBJECT:
                self.shadowManager.updatePlayerTarget(self.__vEntity.model)
            elif state == CameraMovementStates.MOVING_TO_OBJECT:
                self.shadowManager.updatePlayerTarget(None)
            return

    def __doFinalSetup(self, buildIdx):
        if buildIdx != self.__curBuildInd:
            return
        else:
            self.__loadState.load()
            if self.__onLoadedCallback is not None:
                self.__onLoadedCallback()
                self.__onLoadedCallback = None
            if self.__onLoadedAfterRefreshCallback is not None:
                self.__onLoadedAfterRefreshCallback()
                self.__onLoadedAfterRefreshCallback = None
            if self.__vDesc is not None and 'observer' in self.__vDesc.type.tags:
                self.__vEntity.model.visible = False
            return

    def getAnchorParams(self, slotId, areaId, regionIdx):
        if self.__anchorsParams is None:
            self.__initAnchorsParams()
        anchorParams = self.__anchorsParams.get(slotId, {}).get(areaId, {}).get(regionIdx)
        return anchorParams

    def updateAnchorsParams(self, tankPartsToUpdate=TankPartIndexes.ALL):
        if self.__anchorsHelpers is None or self.__anchorsParams is None:
            return
        else:
            self.__updateAnchorsParams(tankPartsToUpdate)
            return

    def getCentralPointForArea(self, areaIdx):

        def _getBBCenter(tankPartName):
            partIdx = TankPartNames.getIdx(tankPartName)
            boundingBox = Math.Matrix(self.__vEntity.model.getBoundsForPart(partIdx))
            bbCenter = boundingBox.applyPoint((0.5, 0.5, 0.5))
            return bbCenter

        if areaIdx == ApplyArea.HULL:
            trackLeftUpFront = self.__vEntity.model.node('HP_TrackUp_LFront').position
            trackRightUpRear = self.__vEntity.model.node('HP_TrackUp_RRear').position
            position = (trackLeftUpFront + trackRightUpRear) / 2.0
            bbCenter = _getBBCenter(TankPartNames.HULL)
            turretJointPosition = self.__vEntity.model.node('HP_turretJoint').position
            position.y = min(turretJointPosition.y, bbCenter.y)
        elif areaIdx == ApplyArea.TURRET:
            position = _getBBCenter(TankPartNames.TURRET)
            position.y = self.__vEntity.model.node('HP_gunJoint').position.y
        elif areaIdx == ApplyArea.GUN_2:
            position = self.__vEntity.model.node('HP_gunJoint').position
        elif areaIdx == ApplyArea.GUN:
            gunJointPos = self.__vEntity.model.node('HP_gunJoint').position
            gunFirePos = self.__vEntity.model.node('HP_gunFire').position
            position = (gunFirePos + gunJointPos) / 2.0
        else:
            position = _getBBCenter(TankPartNames.CHASSIS)
        return position

    def updateCustomization(self, outfit=None, callback=None):
        if self.__isVehicleDestroyed:
            return
        outfit = outfit or self.itemsFactory.createOutfit()
        if self.recreateRequired(outfit):
            self.refresh(outfit, callback)
            return
        self.__updateCamouflage(outfit)
        self.__updatePaint(outfit)
        self.__updateDecals(outfit)
        self.__updateProjectionDecals(outfit)
        self.__updateSequences(outfit)

    def rotateTurretForAnchor(self, anchorId, useStaticTurretYaw=False):
        if self.compoundModel is None:
            return False
        defaultYaw = self.__staticTurretYaw if useStaticTurretYaw else _DEFAULT_TURRET_YAW_ANGLE
        turretYaw = self.__getTurretYawForAnchor(anchorId, defaultYaw)
        currentTurretYaw = Math.Matrix(self.compoundModel.node(TankPartNames.TURRET)).yaw
        if abs(currentTurretYaw - turretYaw) > 0.0001:
            turretYawMatrix = math_utils.createRotationMatrix((turretYaw, 0.0, 0.0))
            self.compoundModel.node(TankPartNames.TURRET, turretYawMatrix)
            return True
        else:
            return False

    def rotateGunToDefault(self, useStaticGunPitch=False):
        if self.compoundModel is None:
            return False
        else:
            localGunMatrix = self.__getGunNode().local
            currentGunPitch = localGunMatrix.pitch
            gunPitchAngle = self.__staticGunPitch if useStaticGunPitch else _DEFAULT_GUN_PITCH_ANGLE
            if abs(currentGunPitch - gunPitchAngle) < 0.0001:
                return False
            gunPitchMatrix = math_utils.createRotationMatrix((0.0, gunPitchAngle, 0.0))
            self.__setGunMatrix(gunPitchMatrix)
            return True

    def __getAnchorHelperById(self, anchorId):
        if anchorId.slotType not in self.__anchorsHelpers:
            return None
        else:
            slotTypeAnchorHelpers = self.__anchorsHelpers[anchorId.slotType]
            if anchorId.areaId not in slotTypeAnchorHelpers:
                return None
            areaAnchorHelpers = slotTypeAnchorHelpers[anchorId.areaId]
            return None if anchorId.regionIdx not in areaAnchorHelpers else areaAnchorHelpers[anchorId.regionIdx]

    def __updateAnchorHelperWithId(self, anchorId, newAnchorHelper):
        self.__anchorsHelpers[anchorId.slotType][anchorId.areaId][anchorId.regionIdx] = newAnchorHelper

    def __getTurretYawForAnchor(self, anchorId, defaultYaw):
        turretYaw = defaultYaw
        if anchorId is not None and hasTurretRotator(self.__vDesc):
            anchorHelper = self.__getAnchorHelperById(anchorId)
            if anchorHelper is not None:
                if anchorHelper.turretYaw is not None:
                    turretYaw = anchorHelper.turretYaw
                else:
                    if anchorHelper.attachedPartIdx == TankPartIndexes.HULL:
                        needsCorrection = anchorId.slotType in (GUI_ITEM_TYPE.PROJECTION_DECAL, GUI_ITEM_TYPE.EMBLEM, GUI_ITEM_TYPE.INSCRIPTION)
                        if needsCorrection:
                            turretYaw = self.__correctTurretYaw(anchorHelper, defaultYaw)
                    anchorHelper = AnchorHelper(anchorHelper.location, anchorHelper.descriptor, turretYaw, anchorHelper.partIdx, anchorHelper.attachedPartIdx)
                    self.__updateAnchorHelperWithId(anchorId, anchorHelper)
        turretYawLimits = self.__vDesc.gun.turretYawLimits
        if turretYawLimits is not None:
            turretYaw = math_utils.clamp(turretYawLimits[0], turretYawLimits[1], turretYaw)
        return turretYaw

    def __updatePaint(self, outfit):
        for fashionIdx, _ in enumerate(TankPartNames.ALL):
            repaint = camouflages.getRepaint(outfit, fashionIdx, self.__vDesc)
            self.c11nComponent.setPartPaint(fashionIdx, repaint)

    def __updateCamouflage(self, outfit):
        for fashionIdx, descId in enumerate(TankPartNames.ALL):
            camo = camouflages.getCamo(self, outfit, fashionIdx, self.__vDesc, descId, self.__vState != 'undamaged')
            self.c11nComponent.setPartCamo(fashionIdx, camo)

    def __updateDecals(self, outfit):
        self.__setupEmblems(outfit)

    def __updateProjectionDecals(self, outfit):
        decals = camouflages.getGenericProjectionDecals(outfit, self.__vDesc)
        self.c11nComponent.setDecals(decals)

    def __updateSequences(self, outfit):
        resources = camouflages.getModelAnimatorsPrereqs(outfit, self.__spaceId)
        if not resources:
            self.__clearModelAnimators()
            return
        BigWorld.loadResourceListBG(tuple(resources), makeCallbackWeak(self.__onAnimatorsLoaded, self.__curBuildInd, outfit))

    def __clearModelAnimators(self):
        for animator in self.__modelAnimators:
            animator.halt()

        self.__modelAnimators = []

    def __onVehicleChanged(self):
        self.__anchorsParams = None
        self.__anchorsHelpers = None
        return

    def __initAnchorsParams(self):
        self.__anchorsParams = {cType:{area:{} for area in Area.ALL} for cType in SLOT_TYPES}
        if self.__anchorsHelpers is None:
            self.__initAnchorsHelpers()
        self.__updateAnchorsParams(TankPartIndexes.ALL)
        return

    def __updateAnchorsParams(self, tankPartsToUpdate):
        tankPartsMatrices = {}
        for tankPartIdx in TankPartIndexes.ALL:
            tankPartName = TankPartIndexes.getName(tankPartIdx)
            tankPartsMatrices[tankPartIdx] = Math.Matrix(self.__vEntity.model.node(tankPartName))

        for slotType in SLOT_TYPES:
            for areaId in Area.ALL:
                anchorHelpers = self.__anchorsHelpers[slotType][areaId]
                for regionIdx, anchorHelper in anchorHelpers.iteritems():
                    attachedPartIdx = anchorHelper.attachedPartIdx
                    if attachedPartIdx not in tankPartsToUpdate:
                        continue
                    anchorLocationWS = self.__getAnchorLocationWS(anchorHelper.location, anchorHelper.partIdx)
                    self.__anchorsParams[slotType][areaId][regionIdx] = AnchorParams(anchorLocationWS, anchorHelper.descriptor, AnchorId(slotType, areaId, regionIdx))

    def __initAnchorsHelpers(self):
        anchorsHelpers = {cType:{area:{} for area in Area.ALL} for cType in SLOT_TYPES}
        for slotType in SLOT_TYPES:
            for areaId in Area.ALL:
                for anchor in g_currentVehicle.item.getAnchors(slotType, areaId):
                    if isinstance(anchor, EmblemSlot):
                        getAnchorHelper = self.__getEmblemAnchorHelper
                        applyTo = None
                    elif isinstance(anchor, BaseCustomizationSlot):
                        getAnchorHelper = self.__getAnchorHelper
                        applyTo = anchor.descriptor.applyTo
                    else:
                        continue
                    if applyTo is not None:
                        regions = REGIONS_BY_SLOT_TYPE[areaId].get(slotType, ())
                        regionIdx = next((i for i, region in enumerate(regions) if applyTo == region), -1)
                    else:
                        regionIdx = len(anchorsHelpers[slotType][areaId])
                    if regionIdx == -1:
                        continue
                    anchorsHelpers[slotType][areaId][regionIdx] = getAnchorHelper(anchor)

        self.__anchorsHelpers = anchorsHelpers
        return

    def __getEmblemAnchorHelper(self, anchor):
        startPos = anchor.rayStart
        endPos = anchor.rayEnd
        normal = startPos - endPos
        normal.normalise()
        up = normal * (anchor.descriptor.rayUp * normal)
        up.normalise()
        position = startPos + (endPos - startPos) * 0.5
        anchorLocation = AnchorLocation(position, normal, up)
        partIdx = anchor.areaId
        attachedPartIdx = self.__getAttachedPartIdx(position, normal, partIdx)
        return AnchorHelper(anchorLocation, anchor.descriptor, None, partIdx, attachedPartIdx)

    def __getAnchorHelper(self, anchor):
        slotType = ANCHOR_TYPE_TO_SLOT_TYPE_MAP[anchor.descriptor.type]
        if slotType in (GUI_ITEM_TYPE.MODIFICATION, GUI_ITEM_TYPE.STYLE):
            hullAABB = self.collisions.getBoundingBox(TankPartIndexes.HULL)
            position = Math.Vector3((hullAABB[1].x + hullAABB[0].x) / 2.0, hullAABB[1].y / 2.0, (hullAABB[1].z + hullAABB[0].z) / 2.0)
            partIdx = TankPartIndexes.HULL
        else:
            position = anchor.anchorPosition
            partIdx = anchor.areaId
        normal = anchor.anchorDirection
        normal.normalise()
        if slotType == GUI_ITEM_TYPE.PROJECTION_DECAL:
            ypr = anchor.descriptor.rotation
            rotationMatrix = Math.Matrix()
            rotationMatrix.setRotateYPR((ypr.y, ypr.x, ypr.z))
            up = rotationMatrix.applyVector((0, 0, -1))
        else:
            up = normal * (Math.Vector3(0, 1, 0) * normal)
        anchorLocation = AnchorLocation(position, normal, up)
        attachedPartIdx = self.__getAttachedPartIdx(position, normal, partIdx)
        return AnchorHelper(anchorLocation, anchor.descriptor, None, partIdx, attachedPartIdx)

    def __getAttachedPartIdx(self, position, normal, tankPartIdx):
        partMatrix = Math.Matrix(self.__vEntity.model.node(TankPartIndexes.getName(tankPartIdx)))
        startPos = position + normal * 0.1
        endPos = position - normal * 0.6
        startPos = partMatrix.applyPoint(startPos)
        endPos = partMatrix.applyPoint(endPos)
        collisions = self.collisions.collideAllWorld(startPos, endPos)
        if collisions is not None:
            for collision in collisions:
                partIdx = collision[3]
                if partIdx in TankPartIndexes.ALL:
                    return partIdx

        return tankPartIdx

    def __correctTurretYaw(self, anchorHelper, defaultYaw):
        if not _SHOULD_CHECK_DECAL_UNDER_GUN:
            return defaultYaw
        else:
            partMatrix = Math.Matrix(self.__vEntity.model.node(TankPartIndexes.getName(anchorHelper.partIdx)))
            turretMat = Math.Matrix(self.compoundModel.node(TankPartNames.TURRET))
            transformMatrix = math_utils.createRTMatrix((turretMat.yaw, partMatrix.pitch, partMatrix.roll), partMatrix.translation)
            anchorLocationWS = self.__applyToAnchorLocation(anchorHelper.location, transformMatrix)
            position = anchorLocationWS.position
            direction = anchorLocationWS.normal
            up = anchorLocationWS.up
            fromTurretToHit = position - turretMat.translation
            if fromTurretToHit.dot(turretMat.applyVector((0, 0, 1))) < 0:
                return defaultYaw
            checkDirWorld = direction * 10.0
            cornersWorldSpace = self.__getDecalCorners(position, direction, up, anchorHelper.descriptor)
            if cornersWorldSpace is None:
                return defaultYaw
            slotType = ANCHOR_TYPE_TO_SLOT_TYPE_MAP[anchorHelper.descriptor.type]
            if slotType == GUI_ITEM_TYPE.PROJECTION_DECAL:
                turretLeftDir = turretMat.applyVector((1, 0, 0))
                turretLeftDir.normalise()
                gunJoin = self.__vEntity.model.node('HP_gunJoint')
                fromGunJointToAnchor = gunJoin.position - position
                decalDiags = (cornersWorldSpace[0] - cornersWorldSpace[2], cornersWorldSpace[1] - cornersWorldSpace[3])
                fromGunToHit = abs(fromGunJointToAnchor.dot(turretLeftDir))
                halfDecalWidth = max((abs(decalDiag.dot(turretLeftDir)) for decalDiag in decalDiags)) * 0.5
                if fromGunToHit > halfDecalWidth * _PROJECTION_DECAL_OVERLAPPING_FACTOR:
                    return 0.0
            result = self.collisions.collideShape(TankPartIndexes.GUN, cornersWorldSpace, checkDirWorld)
            if result < 0.0:
                return defaultYaw
            turretYaw = _HANGAR_TURRET_SHIFT
            gunDir = turretMat.applyVector(Math.Vector3(0, 0, 1))
            if Math.Vector3(0, 1, 0).dot(gunDir * fromTurretToHit) > 0.0:
                turretYaw = -turretYaw
            return turretYaw

    def __getDecalCorners(self, position, direction, up, slotDescriptor):
        cfg = hangarCFG()
        vScale = cfg['v_scale']
        slotType = ANCHOR_TYPE_TO_SLOT_TYPE_MAP[slotDescriptor.type]
        if slotType == GUI_ITEM_TYPE.PROJECTION_DECAL:
            width = slotDescriptor.scale[0] * vScale
            aspect = getProgectionDecalAspect(slotDescriptor)
            height = slotDescriptor.scale[2] * vScale * aspect
        else:
            width = slotDescriptor.size * vScale
            aspect = SLOT_ASPECT_RATIO.get(slotType)
            if aspect is not None:
                height = width * aspect
            else:
                return
        transformMatrix = Math.Matrix()
        transformMatrix.lookAt(position, direction, up)
        transformMatrix.invert()
        result = (Math.Vector3(width * 0.5, height * 0.5, 0),
         Math.Vector3(width * 0.5, -height * 0.5, 0),
         Math.Vector3(-width * 0.5, -height * 0.5, 0),
         Math.Vector3(-width * 0.5, height * 0.5, 0))
        return tuple((transformMatrix.applyPoint(vec) for vec in result))

    def __applyToAnchorLocation(self, anchorLocation, transform):
        position = transform.applyPoint(anchorLocation.position)
        normal = transform.applyVector(anchorLocation.normal)
        up = transform.applyVector(anchorLocation.up)
        if abs(normal.pitch - math.pi / 2) < 0.1:
            normal = Math.Vector3(0, -1, 0) + up * 0.01
            normal.normalise()
        return AnchorLocation(position, normal, up)

    def __getAnchorLocationWS(self, anchorLocation, partIdx):
        partMatrix = Math.Matrix(self.__vEntity.model.node(TankPartIndexes.getName(partIdx)))
        return self.__applyToAnchorLocation(anchorLocation, partMatrix)

    def __getGunNode(self):
        gunNode = self.compoundModel.node(TankNodeNames.GUN_INCLINATION)
        if gunNode is None:
            gunNode = self.compoundModel.node(TankPartNames.GUN)
        return gunNode

    def __setGunMatrix(self, gunMatrix):
        gunNode = self.__getGunNode()
        gunNode.local = gunMatrix
