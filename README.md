# JEC Pipeline

## Setup

Kubeflow is locked behind CERN single sign on. A [CLI tool](https://gitlab.cern.ch/authzsvc/tools/auth-get-sso-cookie), preinstalled on [lxplus8](https://lxplusdoc.web.cern.ch), generates cookies needed to bypass the SSO.
```
auth-get-sso-cookie -u https://ml.cern.ch -o cookies.txt
```

Changes are put into containers stored on CERN's [own registry](https://registry.cern.ch/harbor/projects/34/repositories). Use the credentials from the user profile on harbor to log in to the registry.
```
docker login registry.cern.ch
docker build training -t registry.cern.ch/ml/jec-training
docker push registry.cern.ch/ml/jec-training
docker build serving -t registry.cern.ch/ml/jec-serving
docker push registry.cern.ch/ml/jec-serving
```

## Data

EOS: `/eos/cms/store/group/phys_jetmet/dholmber/jec-data`

Create kerberos secret on Kubeflow

```
kinit <cernid>
kubectl delete secret krb-secret
kubectl create secret generic krb-secret --from-file=/tmp/krb5cc_1000
```

Create s3 secret on Kubeflow
  - Put aws secrets into `secret.yaml` (e.g. from `openstack ec2 credentials list`) 
  - `kubectl apply -f secret.yaml`

## Exporting

python3 train.py -c data/jec_pfn.yaml -n networks/pfn_regressor.py -m outputs/20220315-161332_pfn_regressor_ranger_lr0.005_batch100/net_best_epoch_state.pt --export-onnx model/model.onnx

## Run Pipeline

Install [kfp](https://www.kubeflow.org/docs/components/pipelines/sdk/install-sdk), e.g. on lxplus8: `pip3 install kfp`

```
python3 pipeline.py
```
