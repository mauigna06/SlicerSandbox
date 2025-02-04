# models
ModelA = slicer.util.getNode('ModelA')
ModelB = slicer.util.getNode('ModelB')
ResultingModel = slicer.util.getNode('ResultingModel')
BooleanOperation = "union"

# Set parameters
parameters = {}
parameters["ModelA"] = ModelA.GetID()
parameters["ModelB"] = ModelB.GetID()
parameters["ResultingModel"] = ResultingModel.GetID()
parameters["BooleanOperation"] = BooleanOperation

# Execute
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



