import argparse
import pathlib2
import kubernetes
import time
import yaml
import json
import kfp


def edit_template(
        src, dst, job_name, namespace, 
        pt_path, onnx_path, triton_config, 
        data_config, network_config
    ):
    
    with open(src, 'r') as f:
        template = f.read()

    template = template.replace('JOB_NAME', job_name)
    template = template.replace('NAMESPACE', namespace)
    template = template.replace('PT_PATH', pt_path)
    template = template.replace('ONNX_PATH', onnx_path)
    template = template.replace('TRITON_CONFIG', triton_config)
    template = template.replace('DATA_CONFIG', data_config)
    template = template.replace('NETWORK_CONFIG', network_config)

    with open(dst, 'w') as f:
        f.write(template)

def create_pytorch_job(client, yaml_filepath, namespace):
    print('Load template for submission')
    with open(yaml_filepath, 'r') as f:
        export_spec = yaml.load(f, Loader=yaml.FullLoader)
        print(json.dumps(export_spec, indent=2))

    client.create_namespaced_custom_object(
        group='kubeflow.org',
        version='v1',
        namespace=namespace,
        plural='pytorchjobs',
        body=export_spec,
    )

def delete_pytorch_job(name, namespace):
    print('Delete PyTorch job:', name)
    k8s_co_client.delete_namespaced_custom_object(
        group='kubeflow.org',
        version='v1',
        namespace=namespace,
        plural='pytorchjobs',
        name=name,
        body=kubernetes.client.V1DeleteOptions()
    )

parser = argparse.ArgumentParser(description='Export Params')
parser.add_argument('--id', type=str)
parser.add_argument('--s3-bucket', type=str)
parser.add_argument('--pt-path', type=str)
parser.add_argument('--data-config', type=str)
parser.add_argument('--network-config', type=str)
parser.add_argument('--delete-job', type=str)
parser.add_argument('--model-path', type=str)
args = parser.parse_args()
print('Args:', vars(args))

name = f'export-job-{args.id}'
namespace = kfp.Client().get_user_namespace()

model_path = f'{args.s3_bucket}/{args.id}'
triton_config = f'{model_path}/optimal/config.pbtxt'
onnx_path = f'{model_path}/optimal/1/model.onnx'

edit_template(
    src='template.yaml',
    dst='export_job.yaml',
    job_name=name,
    namespace=namespace,
    pt_path=args.pt_path,
    onnx_path=onnx_path,
    triton_config=triton_config,
    data_config=args.data_config,
    network_config=args.network_config,
)

print('Load incluster config')
kubernetes.config.load_incluster_config()

print('Obtain client')
k8s_co_client = kubernetes.client.CustomObjectsApi()

print('Create export job')
create_pytorch_job(k8s_co_client, 'export_job.yaml', namespace)

while True:
    time.sleep(5)
    
    resource = k8s_co_client.get_namespaced_custom_object(
        group='kubeflow.org',
        version='v1',
        namespace=namespace,
        plural='pytorchjobs',
        name=name
    )
    
    status = resource['status']
    print(status)

    if 'succeeded' in status['replicaStatuses']['Master']:
        print('Export succeeded')
        break

pathlib2.Path(args.model_path).parent.mkdir(parents=True)
pathlib2.Path(args.model_path).write_text(model_path)

if args.delete_job == 'True':
    delete_pytorch_job(name, namespace)
