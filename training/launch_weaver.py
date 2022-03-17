import argparse
import kubernetes
from kubernetes import client
import pathlib2
import yaml
import json
import kfp
import time
import uuid
import os
import re


print('Parse arguments')
parser = argparse.ArgumentParser(description='ML Trainer')
parser.add_argument('--parameters')
parser.add_argument('--timestamp')
parser.add_argument('--data-train')
parser.add_argument('--data-val')
parser.add_argument('--data-test')
parser.add_argument('--network-config')
parser.add_argument('--data-config')
parser.add_argument('--model-prefix')
parser.add_argument('--log')
parser.add_argument('--output-path')
args = parser.parse_args()
print(vars(args))

name = f'jec-hp-tuning-{args.timestamp}'
namespace = kfp.Client().get_user_namespace()

parameters = json.loads(args.parameters)

with open('weaver/job.yaml') as f:
    katib_job = yaml.safe_load(f)

print('Job before:')
print(katib_job)
katib_job['metadata']['name'] = name
katib_job['metadata']['namespace'] = namespace
katib_job['spec']['parameters'] = parameters

template = katib_job['spec']['trialTemplate']['goTemplate']['rawTemplate']
template = re.sub('--data-train', f'--data-train {args.data_train}', template)
template = re.sub('--data-val', f'--data-val {args.data_val}', template)
template = re.sub('--data-test', f'--data-test {args.data_test}', template)
template = re.sub('--network-config', f'--network-config {args.network_config}', template)
template = re.sub('--data-config', f'--data-config {args.data_config}', template)
template = re.sub('--model-prefix', f'--model-prefix {args.model_prefix}', template)
template = re.sub('--log', f'--log {args.log}', template)
katib_job['spec']['trialTemplate']['goTemplate']['rawTemplate'] = template

print('Job after:')
print(katib_job)

print('Load incluster config')
kubernetes.config.load_incluster_config()

print('Obtain CO client')
k8s_co_client = kubernetes.client.CustomObjectsApi()

print('Launch Katib job')
k8s_co_client.create_namespaced_custom_object(
    group='kubeflow.org',
    version='v1alpha3',
    namespace=namespace,
    plural='experiments',
    body=katib_job
)

while True:
    time.sleep(5)
    
    resource = k8s_co_client.get_namespaced_custom_object(
        group='kubeflow.org',
        version='v1alpha3',
        namespace=namespace,
        plural='experiments',
        name=name
    )
    
    status = resource['status']
    print(status)

    if 'completionTime' in status.keys():
        if status['completionTime']:
            print('Optimal trial')
            print(status['currentOptimalTrial'])
            break

pathlib2.Path(args.output_path).parent.mkdir(parents=True)
pathlib2.Path(args.output_path).write_text('s3://jec-data/tmp')

k8s_co_client.delete_namespaced_custom_object(
    group='kubeflow.org',
    version='v1alpha3',
    namespace=namespace,
    plural='experiments',
    name=name,
    body=client.V1DeleteOptions()
)

print(f'Experiment {name} deleted')
