import torch
from models_configs.model import base_Model
from models_configs.configs import *
import torch.nn.functional as f

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
configs = Config()

#Locating model in folders
MODEL_SAVE_PATH = 'models/TS_modelAug18.pt'
#Updated to new model Aug 7, old: ml_model_finetune2.pt

##Loading in base model
uploaded_model = base_Model(configs)

##Loading in weights/settings
chkpoint = torch.load(MODEL_SAVE_PATH, map_location=device)
pretrained_dict = chkpoint['model_state_dict']
uploaded_model.load_state_dict(pretrained_dict)

##Function to predict a ([1,3,128]) shape
def predict(test_case):
	uploaded_model.eval()
	
	with torch.inference_mode():
		output = uploaded_model(test_case)
		predictions, features = output
		
		predicted_index = torch.argmax(predictions, dim=1).float().item()
		probability = f.softmax(predictions, dim=1)
		probability = probability.detach().numpy()
		
		conf = probability[0][int(predicted_index)]
		
	return predicted_index, conf

def convert(test_case):
	output = torch.tensor(test_case).to(dtype=torch.float32).unsqueeze(dim=0).to(device)
	return output
