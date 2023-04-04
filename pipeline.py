import argparse
import uuid
import kfp
from kfp import dsl
import http
import yaml
import json


def load_cookies(cookie_file, domain):
    cookiejar = http.cookiejar.MozillaCookieJar(cookie_file)
    cookiejar.load()
    for cookie in cookiejar:
        if cookie.domain == domain:
            cookies = f'{cookie.name}={cookie.value}'
            break
    return cookies

def get_pipeline(name, description):
    @dsl.pipeline(name=name, description=description)
    def pipeline(
        run_id: str,
        s3_bucket: str,
        data_train: str,
        data_val: str,
        data_test: str,
        data_config: str,
        network_config: str,
        num_replicas: int,
        num_gpus: int,
        num_cpus: int,
        memory: str,
        delete_train_experiment: bool,
        delete_export_job: bool,
    ):

        train = train_op(
            id=run_id,
            s3_bucket=s3_bucket,
            num_replicas=num_replicas,
            num_gpus=num_gpus,
            num_cpus=num_cpus,
            memory=memory,
            data_train=data_train,
            data_val=data_val,
            data_test=data_test,
            data_config=data_config,
            network_config=network_config,
            delete_experiment=delete_train_experiment,
        )

        export = export_op(
            id=run_id,
            s3_bucket=s3_bucket,
            data_config=data_config,
            network_config=network_config,
            delete_job=delete_export_job,
            pt_path=train.outputs['optimal_model_path'],
            network_option=train.outputs['network_option'],
        )

        serve = serve_op(
            model_name=run_id,
            model_path=export.outputs['model_path'],
        )

    return pipeline

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pipeline Params')
    parser.add_argument('--namespace', type=str, default='dholmber', 
                        help='Kubeflow namespace to run pipeline in')
    parser.add_argument('--experiment-name', type=str, default='jec-experiment', 
                        help='name for KFP experiment on Kubeflow')
    parser.add_argument('--num-replicas', type=int, default=1,
                        help='number of nodes to train on')
    parser.add_argument('--num-gpus', type=int, default=1,
                        help='number of gpus per node, limit is 1')
    parser.add_argument('--num-cpus', type=int, default=1, 
                        help='number of cpus to use')
    parser.add_argument('--memory', type=str, default='12Gi', 
                        help='memory in gigabyte')                    
    parser.add_argument('--data-config', type=str, default='data/jec_pfn_open.yaml', 
                        help='data configuration yaml file')
    parser.add_argument('--network-config', type=str, default='networks/pfn_regressor_open.py', 
                        help='network architecture configuration file')
    parser.add_argument('--s3-bucket', type=str, default='s3://jec-data', 
                        help='s3 bucket used by the pipeline for storing models and tensorboard log dirs')
    parser.add_argument('--data-train', type=str, default='s3://jec-data/open/train/*.root',
                        help='training data')
    parser.add_argument('--data-val', type=str, default='s3://jec-data/open/val/*.root',
                        help='validation data')
    parser.add_argument('--data-test', type=str, default='s3://jec-data/open/test/*.root',
                        help='test data')
    parser.add_argument('--delete-train-experiment', action='store_true', default=False,
                        help='whether or not to delete the hp tuning experiment once finished')
    parser.add_argument('--delete-export-job', action='store_true', default=False,
                        help='whether or not to delete the export job once finished')
    args = parser.parse_args()

    # Define pipeline variables
    description = 'Jet Energy Corrections Pipeline'
    network = args.network_config.split("/")[-1].split(".py")[0].replace('_', '-')
    run_id = f'{network}-{uuid.uuid4().hex[:6]}'
    pipeline_name = f'jec-pipeline-{run_id}'
    package_path = f'packages/{pipeline_name}.tar.gz'

    # Import pipeline components
    train_op = kfp.components.load_component_from_file('training/component.yaml')
    export_op = kfp.components.load_component_from_file('exporting/component.yaml')
    serve_op = kfp.components.load_component_from_file('serving/component.yaml')

    # Get pipeline instance
    pipeline = get_pipeline(pipeline_name, description)

    # Compile pipeline
    kfp.compiler.Compiler().compile(pipeline_func=pipeline, package_path=package_path)

    # Load cookies to access Kubeflow at CERN
    cookies = load_cookies(cookie_file='cookies.txt', domain='ml.cern.ch')
    
    # Load Kubeflow pipeline client
    client = kfp.Client(host='https://ml.cern.ch/pipeline', cookies=cookies)

    # Upload pipeline 
    client.upload_pipeline(pipeline_package_path=package_path, pipeline_name=pipeline_name, description=description)

    # Create KFP experiment
    experiment = client.create_experiment(name=args.experiment_name, namespace=args.namespace)

    # Run pipeline
    run = client.run_pipeline(
        pipeline_package_path=package_path,
        experiment_id=experiment.id,
        job_name=f'run-{run_id}',
        params={
            'run_id': run_id,
            's3_bucket': args.s3_bucket,
            'data_train': args.data_train,
            'data_val': args.data_val,
            'data_test': args.data_test,
            'data_config': args.data_config,
            'network_config': args.network_config,
            'num_replicas': args.num_replicas,
            'num_gpus': args.num_gpus,
            'num_cpus': args.num_cpus,
            'memory': args.memory,
            'delete_train_experiment': args.delete_train_experiment,
            'delete_export_job': args.delete_export_job,
        }
    )

    print('Deployed', pipeline_name)
