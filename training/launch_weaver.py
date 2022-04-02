import argparse
import kubernetes
import pathlib2
import yaml
import kfp
import time


print('Parse arguments')
parser = argparse.ArgumentParser(description='ML Trainer')
parser.add_argument('--timestamp')
parser.add_argument('--output-path')
args = parser.parse_args()
print(vars(args))

name = f'jec-hp-tuning-{args.timestamp}'
namespace = kfp.Client().get_user_namespace()

with open('pfn.yaml') as f:
    katib_job = yaml.safe_load(f)

katib_job['metadata']['name'] = name
katib_job['metadata']['namespace'] = namespace

print('Job:')
print(katib_job)

print('Load incluster config')
kubernetes.config.load_incluster_config()

print('Obtain CO client')
k8s_co_client = kubernetes.client.CustomObjectsApi()

print('Launch Katib job')
k8s_co_client.create_namespaced_custom_object(
    group='kubeflow.org',
    version='v1beta1',
    namespace=namespace,
    plural='experiments',
    body=katib_job
)

while True:
    time.sleep(5)
    
    resource = k8s_co_client.get_namespaced_custom_object(
        group='kubeflow.org',
        version='v1beta1',
        namespace=namespace,
        plural='experiments',
        name=name
    )
    
    status = resource['status']
    print(status)

    if 'completionTime' in status.keys():
        if status['completionTime']:
            print('Optimal trial')
            optimal_trial = status['currentOptimalTrial']
            print(optimal_trial)
            break

model_path = 's3://jec-data/pfn/'
values = [pa['value'] for pa in optimal_trial['parameterAssignments']]
model_path += '_'.join(values)
model_path += '.pt'
print('model path:', model_path)

pathlib2.Path(args.output_path).parent.mkdir(parents=True)
pathlib2.Path(args.output_path).write_text(model_path)

k8s_co_client.delete_namespaced_custom_object(
    group='kubeflow.org',
    version='v1beta1',
    namespace=namespace,
    plural='experiments',
    name=name,
    body=kubernetes.client.V1DeleteOptions()
)

print(f'Experiment {name} deleted')
