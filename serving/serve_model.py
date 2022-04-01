import argparse
import kfp
import kubernetes
from kubernetes import config
import yaml


def edit_template(src, dst, args, namespace):
    with open(src, 'r') as f:
        template = f.read()

    template = template.replace('MODEL_NAME', args.model_name)
    template = template.replace('NAMESPACE', namespace)
    template = template.replace('STORAGE_URI', args.model_path)

    with open(dst, 'w') as f:
        f.write(template)

def create_inferenceservice(client, yaml_filepath, namespace):
    print('yaml_filepath')
    print(yaml_filepath)

    print('Load template for submission')
    with open(yaml_filepath, 'r') as f:
        infs_spec = yaml.load(f, Loader=yaml.FullLoader)
        print(infs_spec)

    client.create_namespaced_custom_object(
        group='serving.kubeflow.org',
        version='v1beta1',
        namespace=namespace,
        plural='inferenceservices',
        body=infs_spec
    )


parser = argparse.ArgumentParser(description='Serving Params')
parser.add_argument('--model_name', type=str)
parser.add_argument('--model_path', type=str)
args = parser.parse_args()
namespace = kfp.Client().get_user_namespace()

print('args:')
print(vars(args))

print('namespace:')
print(namespace)

print('Edit template')
edit_template(
    src='template.yaml',
    dst='inference_service.yaml',
    args=args,
    namespace=namespace
)

print('Load incluster config')
config.load_incluster_config()

print('Obtain client')
k8s_co_client = kubernetes.client.CustomObjectsApi()

print('Create CRD')
create_inferenceservice(k8s_co_client, 'inference_service.yaml', namespace)
