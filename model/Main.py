import pickle
import torch
import numpy as np
from Dataset import Dataset
from RecurrentGCN import T_Closure
from torch_geometric.loader import DataLoader
from TemporalDataLoader import DataLoader
from sklearn.metrics import precision_recall_curve
import warnings
warnings.filterwarnings("ignore")

def get_f1(p,r):
    return 1.25*(p*r)/(0.25*p+r)

print("loading dataset...")
result_path = '../Dataset/111320.pickle'
#dataset = Dataset('../Dataset/test_set_102425_large.csv', None, 10, 50)
dataset = Dataset('../Dataset/train_set_large.csv', '../Dataset/test_set_111320_large.csv', 10, 50)
print("get_train_sets")
train_dataset, train_ids = dataset.get_train_set()
print("get_test_set")
test_dataset, test_ids = dataset.get_test_set()

train_dataLoader = DataLoader(train_dataset, batch_size=20, shuffle=True)
test_dataLoader = DataLoader(test_dataset, batch_size=20, shuffle=False)

DEVICE = torch.device('cuda:0') # cuda
train_size = len(train_dataset)
test_size = len(test_dataset)

print("Done")
print("Train num: " + str(len(train_dataset)))
print("Test num: " + str(len(test_dataset)))

model = T_Closure(150,1,10,1).to(DEVICE)
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
criterion = torch.nn.BCELoss()

f_best = 0
for epoch in range(101):
    print("Epoch" + str(epoch))
    epoch_Loss = 0
    model.train()
    model.clean()
    for batch in train_dataLoader:
        h_classcify, target_classcify, traj_aux_loss = model(batch, 'train')
        #print(h_classcify)
        Loss = criterion(h_classcify, target_classcify.to(DEVICE))
        Loss += traj_aux_loss
        Loss.backward()
        optimizer.step()
        optimizer.zero_grad()
        epoch_Loss += Loss
    print("Loss: " + str(epoch_Loss/train_size))
    
    if epoch %5 == 0:
        model.eval()
        all_prob = np.array([])
        all_y = np.array([])
        all_target = np.array([])
        print("eval in test_dataset")
        right_list = []
        fp_list = []
        fn_list = []
        for batch in test_dataLoader:
            h_classcify, target_classcify, traj_aux_loss = model(batch, 'test')
            y = h_classcify.detach().cpu()
            target = target_classcify.float().cpu().numpy()

            all_prob = np.append(all_prob, y)
            all_target = np.append(all_target, target)

        if epoch % 5 == 0:
            precision, recall, thresholds = precision_recall_curve(all_target, all_prob)
            p_np = np.array(precision)
            r_np = np.array(recall)
            t_np = np.array(thresholds)
            p_list = []
            r_list  =[]
            t_list = []
            f_score = [get_f1(p_np[i], r_np[i]) for i in range(len(p_np))]
            f_score_max_index = np.where(f_score == np.nanmax(f_score))[0][0]
            f_now = f_score[f_score_max_index]
            if f_now >= f_best:
                f_best = f_now
                pickle.dump([[precision, recall, thresholds], [test_ids, all_prob, all_target]], open(result_path,"wb"))
                torch.save(model.state_dict(), '111320.pt')

            for i in [0.95, 0.9, 0.8, 0.7]:
                p_filter = p_np[p_np >=i]
                if len(p_filter) !=0:
                    r_filter = r_np[-len(p_filter):]
                    t_filter = t_np[-len(p_filter):]
                    p_list.append(p_filter[0])
                    r_list.append(r_filter[0])
                    t_list.append(t_filter[0])
                else:
                    p_list.append(0)
                    r_list.append(0)
                    t_list.append(0)
            print(p_list)
            print(r_list)
            print(t_list)
        
    
    