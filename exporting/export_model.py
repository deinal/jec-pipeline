import argparse
import pathlib2
import kubernetes
import yaml
import kfp


def edit_template(src, dst, job_name, namespace, pt_path, onnx_path):
    with open(src, 'r') as f:
        template = f.read()

    template = template.replace('JOB_NAME', job_name)
    template = template.replace('NAMESPACE', namespace)
    template = template.replace('PT_PATH', pt_path)
    template = template.replace('ONNX_PATH', onnx_path)

    with open(dst, 'w') as f:
        f.write(template)

def create_export_job(client, yaml_filepath, namespace):
    print('Load template for submission')
    with open(yaml_filepath, 'r') as f:
        export_spec = yaml.load(f, Loader=yaml.FullLoader)
        print(export_spec)

    client.create_namespaced_custom_object(
        group='kubeflow.org',
        version='v1',
        namespace=namespace,
        plural='pytorchjobs',
        body=export_spec,
    )

parser = argparse.ArgumentParser(description='Export Params')
parser.add_argument('--timestamp', type=str)
parser.add_argument('--input-path', type=str)
parser.add_argument('--model-path', type=str)
args = parser.parse_args()
print('args:')
print(vars(args))

name = f'export-job-{args.timestamp}'
namespace = kfp.Client().get_user_namespace()

model_path = f's3://jec-data/{args.timestamp}'
onnx_path = f'{model_path}/pfn/1/model.onnx'

edit_template(
    src='template.yaml',
    dst='export_job.yaml',
    job_name=name,
    namespace=namespace,
    pt_path=args.input_path,
    onnx_path=onnx_path
)

print('Load incluster config')
kubernetes.config.load_incluster_config()

print('Obtain client')
k8s_co_client = kubernetes.client.CustomObjectsApi()

print('Create export job')
create_export_job(k8s_co_client, 'export_job.yaml', namespace)

pathlib2.Path(args.model_path).parent.mkdir(parents=True)
pathlib2.Path(args.model_path).write_text(model_path)
