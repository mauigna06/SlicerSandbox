import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

#
# CombineModels
#

class CombineModels(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Combine Models"
    self.parent.categories = ["Surface Models"]
    self.parent.dependencies = []
    self.parent.contributors = ["Andras Lasso (PerkLab)"]
    self.parent.helpText = """
This module can perform Boolean operations on model nodes (surface meshes).</a>.
"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
The module uses https://github.com/zippy84/vtkbool for processing.
"""

    for subfolder in ['Release', 'Debug', 'RelWithDebInfo', 'MinSizeRel', '.']:
      logicPath = os.path.realpath(os.path.join(os.path.dirname(__file__), '../qt-loadable-modules/'+subfolder)).replace('\\','/')
      if os.path.exists(logicPath):
        import sys
        sys.path.append(logicPath)
        break

#
# CombineModelsWidget
#

class CombineModelsWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/CombineModels.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = CombineModelsLogic()

    # Connections

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.ui.inputModelASelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.inputModelBSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.outputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)

    self.ui.operationUnionRadioButton.connect("toggled(bool)", lambda toggled, op="union": self.operationButtonToggled(op))
    self.ui.operationIntersectionRadioButton.connect("toggled(bool)", lambda toggled, op="intersection": self.operationButtonToggled(op))
    self.ui.operationDifferenceRadioButton.connect("toggled(bool)", lambda toggled, op="difference": self.operationButtonToggled(op))
    self.ui.operationDifference2RadioButton.connect("toggled(bool)", lambda toggled, op="difference2": self.operationButtonToggled(op))

    self.ui.triangulateInputsCheckBox.connect("stateChanged(int)", self.updateParameterNodeFromGUI)

    # Spin Boxes
    self.ui.numberOfRetriesSpinBox.valueChanged.connect(self.updateParameterNodeFromGUI)
    self.ui.randomTranslationMagnitudeSpinBox.valueChanged.connect(self.updateParameterNodeFromGUI)

    self.ui.backendSelectorComboBox.currentTextChanged.connect(self.updateParameterNodeFromGUI)

    # Buttons
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.toggleVisibilityButton.connect('clicked(bool)', self.onToggleVisibilityButton)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # Update node selectors and sliders
    self.ui.inputModelASelector.setCurrentNode(self._parameterNode.GetNodeReference("InputModelA"))
    self.ui.inputModelBSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputModelB"))
    self.ui.outputModelSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputModel"))

    operation = self._parameterNode.GetParameter("Operation")
    self.ui.operationUnionRadioButton.checked = (operation == "union")
    self.ui.operationIntersectionRadioButton.checked = (operation == "intersection")
    self.ui.operationDifferenceRadioButton.checked = (operation == "difference")
    self.ui.operationDifference2RadioButton.checked = (operation == "difference2")

    # Update buttons states and tooltips
    if (self._parameterNode.GetNodeReference("InputModelA")
      and self._parameterNode.GetNodeReference("InputModelB")):
      self.ui.applyButton.toolTip = "Compute output model"
      self.ui.applyButton.enabled = True
    else:
      self.ui.applyButton.toolTip = "Select input model nodes"
      self.ui.applyButton.enabled = False

    self.ui.toggleVisibilityButton.enabled = (self._parameterNode.GetNodeReference("OutputModel") is not None)

    # translate randomly order of magnitude (value is negative by default)
    randomTranslationMagnitude = int(self._parameterNode.GetParameter("randomTranslationMagnitude"))
    self.ui.randomTranslationMagnitudeSpinBox.value = randomTranslationMagnitude

    numberOfRetries = int(self._parameterNode.GetParameter("numberOfRetries"))
    self.ui.numberOfRetriesSpinBox.value = numberOfRetries
    if numberOfRetries > 0:
      self.ui.numberOfRetriesSpinBox.toolTip = "Model B will be randomized if operation fails"
      self.ui.randomTranslationMagnitudeSpinBox.enabled = True
      randomTranslationAmount = 10**-randomTranslationMagnitude
      self.ui.randomTranslationMagnitudeSpinBox.toolTip = f"If the operation fails, it will retry with a random translation of {randomTranslationAmount}"
    else:
      self.ui.numberOfRetriesSpinBox.toolTip = "Computation will be attempted only with exact inputs."
      self.ui.randomTranslationMagnitudeSpinBox.enabled = False
      self.ui.randomTranslationMagnitudeSpinBox.toolTip = "Set a number of retries to larger than 0"

    self.ui.triangulateInputsCheckBox.checked = self._parameterNode.GetParameter("triangulateInputs") == "True"

    self.ui.backendSelectorComboBox.setCurrentText(self._parameterNode.GetParameter("Backend"))

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    self._parameterNode.SetNodeReferenceID("InputModelA", self.ui.inputModelASelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("InputModelB", self.ui.inputModelBSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("OutputModel", self.ui.outputModelSelector.currentNodeID)

    self._parameterNode.SetParameter("numberOfRetries", str(self.ui.numberOfRetriesSpinBox.value))
    self._parameterNode.SetParameter("randomTranslationMagnitude", str(self.ui.randomTranslationMagnitudeSpinBox.value))

    self._parameterNode.SetParameter("triangulateInputs", "true" if self.ui.triangulateInputsCheckBox.checked else "false")

    self._parameterNode.SetParameter("Backend", self.ui.backendSelectorComboBox.currentText)

    self._parameterNode.EndModify(wasModified)

  def operationButtonToggled(self, operation):
    self._parameterNode.SetParameter("Operation", operation)

  def onApplyButton(self):
    """
    Run processing when user clicks "Apply" button.
    """
    try:
      qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
      # Add a new node for output, if no output node is selected
      if not self._parameterNode.GetNodeReference("OutputModel"):
        outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        outputModel.CreateDefaultDisplayNodes()
        self._parameterNode.SetNodeReferenceID("OutputModel", outputModel.GetID())

      # Compute output
      self.logic.process(
        self._parameterNode.GetNodeReference("InputModelA"),
        self._parameterNode.GetNodeReference("InputModelB"),
        self._parameterNode.GetNodeReference("OutputModel"),
        self._parameterNode.GetParameter("Operation"),
        int(self._parameterNode.GetParameter("numberOfRetries")),
        int(self._parameterNode.GetParameter("randomTranslationMagnitude")),
        self._parameterNode.GetParameter("triangulateInputs") == "true",
        self._parameterNode.GetParameter("Backend")
      )

    except Exception as e:
      slicer.util.errorDisplay("Failed to compute results: "+str(e))
      import traceback
      traceback.print_exc()
    finally:
      qt.QApplication.restoreOverrideCursor()

  def onToggleVisibilityButton(self):
    outputModel = self._parameterNode.GetNodeReference("OutputModel")
    inputModelA = self._parameterNode.GetNodeReference("InputModelA")
    inputModelB = self._parameterNode.GetNodeReference("InputModelB")
    if not outputModel:
      return
    outputModel.CreateDefaultDisplayNodes()
    showOutput = not outputModel.GetDisplayNode().GetVisibility()
    inputModelA.GetDisplayNode().SetVisibility(not showOutput)
    inputModelB.GetDisplayNode().SetVisibility(not showOutput)
    outputModel.GetDisplayNode().SetVisibility(showOutput)


#
# CombineModelsLogic
#

class CombineModelsLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Operation"):
      parameterNode.SetParameter("Operation", "union")
    if not parameterNode.GetParameter("numberOfRetries"):
      parameterNode.SetParameter("numberOfRetries", "2")
    if not parameterNode.GetParameter("randomTranslationMagnitude"):
      parameterNode.SetParameter("randomTranslationMagnitude", "4")
    if not parameterNode.GetParameter("triangulateInputs"):
      parameterNode.SetParameter("triangulateInputs", "true")
    if not parameterNode.GetParameter("Backend"):
      parameterNode.SetParameter("Backend", "vtkbool")

  def getInputModelMeshInOutputModelCoordinateSystem(self, inputModelNode, outputModelNode):
      transformToOutput = vtk.vtkGeneralTransform()
      slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(
        inputModelNode.GetParentTransformNode(), 
        outputModelNode.GetParentTransformNode(), 
        transformToOutput
      )
      transformer = vtk.vtkTransformPolyDataFilter()
      transformer.SetTransform(transformToOutput)
      transformer.SetInputData(inputModelNode.GetMesh())
      transformer.Update()
      return transformer.GetOutput()
  
  def applyRandomTranslationToPolydata(self, polyData, randomTranslationOrderOfMagnitude):
    unitVector = [vtk.vtkMath.Random()-0.5 for _ in range(3)]
    vtk.vtkMath.Normalize(unitVector)
    import numpy as np
    translationVector = np.array(unitVector) * (10**-randomTranslationOrderOfMagnitude)
    perturbationTransform = vtk.vtkTransform()
    perturbationTransform.Translate(translationVector)
    perturbationTransformer = vtk.vtkTransformPolyDataFilter()
    perturbationTransformer.SetTransform(perturbationTransform)
    perturbationTransformer.SetInputData(polyData)
    perturbationTransformer.Update()
    return perturbationTransformer.GetOutput()
  
  def doMeshesCollide(self, polydataA, polydataB):
    collisionDetectionFilter = vtk.vtkCollisionDetectionFilter()
    collisionDetectionFilter.SetInputData(0, polydataA)
    collisionDetectionFilter.SetInputData(1, polydataB)
    identityMatrix = vtk.vtkMatrix4x4()
    collisionDetectionFilter.SetMatrix(0,identityMatrix)
    collisionDetectionFilter.SetMatrix(1,identityMatrix)
    collisionDetectionFilter.SetCollisionModeToFirstContact()
    collisionDetectionFilter.Update()
    meshesAreIntersecting = collisionDetectionFilter.GetNumberOfContacts() > 0
    return meshesAreIntersecting
    
  def quickSolveBooleanOperation(self, meshA, meshB, operation):
    polydataCombined = None
    
    if operation == 'union':
      # models do not touch so we can simply append them
      appendFilter = vtk.vtkAppendPolyData()
      appendFilter.AddInputData(meshA)
      appendFilter.AddInputData(meshB)
      appendFilter.Update()
      polydataCombined = appendFilter.GetOutput()
    elif operation == 'intersection':
      # models do not touch so we return an empty model
      polydataCombined = vtk.vtkPolyData()
    elif operation == 'difference':  # A-B
      polydataCombined = meshA
    elif operation == 'difference2':  # B-A
      polydataCombined = meshB
    
    return polydataCombined
  
  def calculateSurfaceArea(self, polydata):
    triangleFilter = vtk.vtkTriangleFilter()
    triangleFilter.SetInputData(polydata)
    triangleFilter.SetPassLines(0)
    triangleFilter.Update()
    
    massProperties = vtk.vtkMassProperties()
    massProperties.SetInputData(triangleFilter.GetOutput())
    return massProperties.GetSurfaceArea()
  
  def getMeshesWithSimilarAreaPerTriangle(self, meshA, meshB):
    meshAAreaPerTriangle = self.calculateSurfaceArea(meshA) / meshA.GetNumberOfCells()
    meshBAreaPerTriangle = self.calculateSurfaceArea(meshB) / meshB.GetNumberOfCells()

    linearSubdivisionFilter = vtk.vtkLinearSubdivisionFilter()
    NEW_TRIANGLES_PER_SUBDIVISION = 4

    import numpy as np
    if meshAAreaPerTriangle >= meshBAreaPerTriangle:
      # subdivide meshA so its area per triangle is the nearer to meshB's 
      areaPerTriangleFactor = meshAAreaPerTriangle / meshBAreaPerTriangle
      numberOfSubdivisions = int(np.log2(areaPerTriangleFactor)/np.log2(NEW_TRIANGLES_PER_SUBDIVISION))
      linearSubdivisionFilter.SetInputData(meshA)
      linearSubdivisionFilter.SetNumberOfSubdivisions(numberOfSubdivisions)
      linearSubdivisionFilter.Update()
      meshA = linearSubdivisionFilter.GetOutput()
    elif meshBAreaPerTriangle > meshAAreaPerTriangle:
      # subdivide meshB so its area per triangle is the nearer to meshA's 
      areaPerTriangleFactor = meshBAreaPerTriangle / meshAAreaPerTriangle
      numberOfSubdivisions = int(np.log2(areaPerTriangleFactor)/np.log2(NEW_TRIANGLES_PER_SUBDIVISION))
      linearSubdivisionFilter.SetInputData(meshB)
      linearSubdivisionFilter.SetNumberOfSubdivisions(numberOfSubdivisions)
      linearSubdivisionFilter.Update()
      meshB = linearSubdivisionFilter.GetOutput()
    
    return meshA, meshB
  
  def executeVtkboolFilter(
    self, 
    operation, 
    meshA, 
    meshB, 
    numberOfRetries=0, 
    randomizedTranslation=None
  ):
    import vtkSlicerCombineModelsModuleLogicPython as vtkbool
    combine = vtkbool.vtkPolyDataBooleanFilter()
    if operation == 'union':
      combine.SetOperModeToUnion()
    elif operation == 'intersection':
      combine.SetOperModeToIntersection()
    elif operation == 'difference':
      combine.SetOperModeToDifference()
    else:
      raise ValueError("Invalid operation: "+operation)
    
    combine.SetInputData(0, meshA)
    combine.SetInputData(1, meshB)
    combine.Update()

    if combine.GetOutput().GetNumberOfPoints() > 0:
      return combine.GetOutput()

    if numberOfRetries >= 1:
      for i in range(numberOfRetries):
        combine.SetInputData(1, randomizedTranslation(meshB))
        combine.Update()
        if combine.GetOutput().GetNumberOfPoints() > 0:
          break
    
    return combine.GetOutput()
  
  def executeGeogramCLIWithParameters(
      self,
      ModelA_ID,
      ModelB_ID,
      ResultingModel_ID,
      BooleanOperation
  ):
    parameters = {}
    parameters["ModelA"] = ModelA_ID
    parameters["ModelB"] = ModelB_ID
    parameters["ResultingModel"] = ResultingModel_ID
    parameters["BooleanOperation"] = BooleanOperation

    robustBooleanOperation = slicer.modules.geogrambooleanoperation
    cliNode = slicer.cli.runSync(robustBooleanOperation, None, parameters)
    # Process results
    if cliNode.GetStatus() & cliNode.ErrorsMask:
      # error
      errorText = cliNode.GetErrorText()
      slicer.mrmlScene.RemoveNode(cliNode)
      raise ValueError("CLI execution failed: " + errorText)
    # success
    slicer.mrmlScene.RemoveNode(cliNode)
  
  def executeGeogramFilter(self, outputModel, operation, meshA, meshB, numberOfRetries=0, randomizedTranslation=None):
    # temporary models to store the polydata, they will be deleted after processing
    modelsLogic = slicer.modules.models.logic()
    modelACopy = modelsLogic.AddModel(meshA)
    modelBCopy = modelsLogic.AddModel(meshB)

    self.executeGeogramCLIWithParameters(
      modelACopy.GetID(),
      modelBCopy.GetID(),
      outputModel.GetID(),
      operation
    )

    resultIsValid = outputModel.GetPolyData().GetNumberOfPoints() > 0
    if resultIsValid:
      slicer.mrmlScene.RemoveNode(modelACopy)
      slicer.mrmlScene.RemoveNode(modelBCopy)
      return

    if numberOfRetries >= 1:
      for i in range(numberOfRetries):
        modelBCopy.SetAndObservePolyData(randomizedTranslation(modelBCopy.GetPolyData()))
        self.executeGeogramCLIWithParameters(
          modelACopy.GetID(),
          modelBCopy.GetID(),
          outputModel.GetID(),
          operation
        )

        resultIsValid = outputModel.GetPolyData().GetNumberOfPoints() > 0
        if resultIsValid:
          break
    
    slicer.mrmlScene.RemoveNode(modelACopy)
    slicer.mrmlScene.RemoveNode(modelBCopy)
    return
  
  def executeManifoldFilter(self, operation, meshA, meshB, numberOfRetries=0, randomizedTranslation=None):
    result = self.meshBooleanOperationAlternative(operation, meshA, meshB, backend="manifold")
    if result.GetNumberOfPoints() > 0:
      return result

    if numberOfRetries >= 1:
      for i in range(numberOfRetries):
        result = self.meshBooleanOperationAlternative(operation, meshA, randomizedTranslation(meshB), backend="manifold")
        if result.GetNumberOfPoints() > 0:
          break
    
    return result
  
  def executeBlenderFilter(self, operation, meshA, meshB, numberOfRetries=0, randomizedTranslation=None):
    result = self.meshBooleanOperationAlternative(operation, meshA, meshB, backend="blender")
    if result.GetNumberOfPoints() > 0:
      return result

    if numberOfRetries >= 1:
      for i in range(numberOfRetries):
        result = self.meshBooleanOperationAlternative(operation, meshA, randomizedTranslation(meshB), backend="blender")
        if result.GetNumberOfPoints() > 0:
          break
    
    return result
  
  def triangulateMesh(self, polyData):
    triangleFilter = vtk.vtkTriangleFilter()
    triangleFilter.SetInputData(polyData)
    triangleFilter.Update()
    return triangleFilter.GetOutput()
  
  def process(
    self, 
    inputModelA, 
    inputModelB, 
    outputModel, 
    operation, 
    numberOfRetries = 2, 
    randomTranslationMagnitude = 4, 
    triangulateInputs = True,
    backend = "vtkbool"
  ):
    """
    Run the processing algorithm.
    Can be used without GUI widget.
    :param inputModelA: first input model node
    :param inputModelB: second input model node
    :param outputModel: result model node, if empty then a new output node will be created
    :param operation: union, intersection, difference, difference2
    :param numberOfRetries: number of retries if operation fails
    :param randomTranslationMagnitude: order of magnitude of random translation
    :param triangulateInputs: if True, input meshes will be triangulated
    :param backend: vtkbool, geogram, manifold, blender
    """

    if not inputModelA or not inputModelB or not outputModel:
      raise ValueError("Input or output model nodes are invalid")

    #import time
    #startTime = time.time()
    #logging.info('Processing started')

    # check if operation is valid
    if operation not in ['union','intersection','difference','difference2']:
      raise ValueError("Invalid operation: "+operation)
    
    # swap input models for difference2 operation
    if operation == 'difference2':
        inputModelA, inputModelB = inputModelB, inputModelA
        operation = 'difference'
    
    # meshes to be combined
    meshA = self.getInputModelMeshInOutputModelCoordinateSystem(inputModelA, outputModel)
    meshB = self.getInputModelMeshInOutputModelCoordinateSystem(inputModelB, outputModel)

    if triangulateInputs:
      meshA = self.triangulateMesh(meshA)
      meshB = self.triangulateMesh(meshB)
    
    if not self.doMeshesCollide(meshA, meshB):
      resultMesh = self.quickSolveBooleanOperation(meshA, meshB, operation)
      outputModel.SetAndObservePolyData(resultMesh)
      return

    # do subdivision to achieve same order of magnitude area per triangle ratio on both meshes
    meshA, meshB = self.getMeshesWithSimilarAreaPerTriangle(meshA, meshB)
    
    randomizedTranslation = (
      lambda dmesh: self.applyRandomTranslationToPolydata(dmesh, randomTranslationMagnitude)
    )

    # select the backend filter or CLI
    if backend == "vtkbool":
      outputMesh = self.executeVtkboolFilter(
        operation, meshA, meshB, numberOfRetries, randomizedTranslation
      )
      outputModel.SetAndObservePolyData(outputMesh)
      # The filter creates a few scalars, don't show them by default, as they would be somewhat distracting
      outputModel.GetDisplayNode().SetScalarVisibility(False)
      return
    elif backend == "geogram":
      self.executeGeogramFilter(
        outputModel, operation, meshA, meshB, numberOfRetries, randomizedTranslation
      )
      return
    
    if not self.installBooleanOperationsAlternativeBackend():
        return
    if backend == "manifold":
      outputMesh = self.executeManifoldFilter(
        operation, meshA, meshB, numberOfRetries, randomizedTranslation
      )
      outputModel.SetAndObservePolyData(outputMesh)
      return
    elif backend == "blender":
      outputMesh = self.executeBlenderFilter(
        operation, meshA, meshB, numberOfRetries, randomizedTranslation
      )
      outputModel.SetAndObservePolyData(outputMesh)
      return

    #stopTime = time.time()
    #logging.info('Processing completed in {0:.2f} seconds'.format(stopTime-startTime))
  
  @staticmethod
  def installBooleanOperationsAlternativeBackend(force=False):
    # install required trimesh package
    try:
      import trimesh
    except ModuleNotFoundError as e:
      if force or slicer.util.confirmOkCancelDisplay("This function requires 'trimesh' Python package. Click OK to install it now."):
        slicer.util.pip_install("trimesh")
      else:
        return False
      
    # install required manifold3d package
    try:
      import manifold3d
    except ModuleNotFoundError as e:
      if force or slicer.util.confirmOkCancelDisplay("This function requires 'manifold3d' Python package. Click OK to install it now."):
        slicer.util.pip_install("manifold3d") # needs c++ compilation
      else:
        return False
      
    # install required networkx package
    try:
      import networkx
    except ModuleNotFoundError as e:
      if force or slicer.util.confirmOkCancelDisplay("This function requires 'networkx' Python package. Click OK to install it now."):
        slicer.util.pip_install("networkx")
      else:
        return False
    
    # install required pyvista package
    try:
      import pyvista
    except ModuleNotFoundError as e:
      if force or slicer.util.confirmOkCancelDisplay("This function requires 'pyvista' Python package. Click OK to install it now."):
        slicer.util.pip_install("pyvista")
      else:
        return False
    
    return True
  
  def toTrimesh(self, polyData, doRepairMesh=True):
    """
    Converts the input VTK mesh to trimesh format.
    """
    import pyvista as pv
    pv_mesh = pv.PolyData(polyData)
    pv_mesh = pv_mesh.extract_surface().triangulate()
    faces_as_array = pv_mesh.faces.reshape((pv_mesh.n_cells, 4))[:, 1:]
    import trimesh
    mesh = trimesh.Trimesh(pv_mesh.points, faces_as_array)
    if doRepairMesh:
        mesh.remove_duplicate_faces()
        mesh.remove_unreferenced_vertices()
        mesh.remove_degenerate_faces()
        #mesh.fill_holes()
        mesh.fix_normals()
    return mesh

  def meshBooleanOperationAlternative(self, operation, model1PolyData, model2PolyData, backend="manifold"):
    """Apply given boolean operation between two models. The output overwrites the 1st input model"""
    model1_trimesh = self.toTrimesh(model1PolyData)
    model2_trimesh = self.toTrimesh(model2PolyData)
    meshes = [model1_trimesh, model2_trimesh]

    import trimesh
    if operation == "union":
        op = trimesh.boolean.union
    elif operation == "intersection":
        op = trimesh.boolean.intersection
    elif operation == "difference":
        op = trimesh.boolean.difference
    elif operation == "difference2":
        op = trimesh.boolean.difference
        meshes = [model2_trimesh, model1_trimesh]

    supported_backends = ["manifold", "blender"]
    if backend not in supported_backends:
        backend = "manifold"

    import pyvista as pv
    # https://github.com/mikedh/trimesh/issues/2253 there is a problem here
    kwargs = {}
    kwargs["check_volume"] = False
    return pv.wrap(op(meshes, engine=backend, check_volume=False, kwargs=kwargs))

#
# CombineModelsTest
#

class CombineModelsTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_CombineModels1()

  def test_CombineModels1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    sphere = vtk.vtkSphereSource()
    sphere.SetRadius(30)
    inputModelA = slicer.modules.models.logic().AddModel(sphere.GetOutputPort())

    cylinder = vtk.vtkCylinderSource()
    cylinder.SetRadius(20)
    cylinder.SetHeight(75)
    inputModelB = slicer.modules.models.logic().AddModel(cylinder.GetOutputPort())

    # Test the module logic

    logic = CombineModelsLogic()

    for operation in ['union', 'intersection', 'difference', 'difference2']:
      outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", 'Output '+operation)
      outputModel.CreateDefaultDisplayNodes()
      logic.process(inputModelA, inputModelB, outputModel, operation)
      self.assertTrue(outputModel.GetPolyData().GetNumberOfPoints()>0)

    self.delayDisplay('Test passed')
