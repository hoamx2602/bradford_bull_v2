from roboflow import Roboflow
rf = Roboflow(api_key="FJ8fMyhOT1GNj4OFw4Ff")
project = rf.workspace("ans-workspace-smynf").project("Auto Black")
dataset = project.version(1).download("coco")