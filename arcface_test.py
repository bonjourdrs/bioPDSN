import torch
from easydict import EasyDict as edict
from lib.Learner import face_learner
from lib.mtcnn import MTCNN
from torchvision import transforms as trans
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='for arcface test')
    parser.add_argument("-i", "--input_size", help="input size", default="112,112", type=str)
    parser.add_argument("-e", "--embedding_size", help="embedding size",default=512, type=int)
    parser.add_argument("-u", "--use_mobilefacenet", help="Wheter use mobilefacenet ", default=False, type=bool)
    parser.add_argument('-d','--net_depth',help='how many layers [50,100,152]',default=50, type=int)
    parser.add_argument("-n", "--net_mode", help="which network, [ir, ir_se, mobilefacenet]",default='ir_se', type=str)
    parser.add_argument("-threshold", "--threshold", help="Threshold to use in verification", default=0.5, type=float)
    parser.add_argument("-drop", "--drop_ratio", help="Drop ratio", default=0.6, type=float)
    parser.add_argument("-device", "--device", help="Which device use (cpu or gpu)", default='cpu', type=str)
    parser.add_argument("-w", "--weights_path", help="Path to weights", default=None, type=str)
    parser.add_argument("-transform","--transform", help="Input transform",default=False,type=bool)
    args = parser.parse_args()

    '''
    conf.test_transform = trans.Compose([
                    trans.ToTensor(),
                    trans.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
                ])
    '''
    #mtcnn = MTCNN()
    #print("mtcnn loaded")


    learner = face_learner(args,inference=True)
    model = learner.model
    if(args.device == 'cpu'):
        model.load_state_dict(torch.load(args.weights_path,map_location=torch.device('cpu')))
    else:
        model.load_state_dict(torch.load(args.weights_path))
    model.eval()
    print("Modelo cargado correctamente !! wuju")

