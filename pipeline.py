import kfp
from kfp import dsl
import http
import yaml
import json
from datetime import datetime

timestamp = datetime.now().strftime("%d%m%Y-%H%M%S")
pipeline_name = f'jec-pipeline-{timestamp}'
description = 'Jet Energy Corrections Pipeline'
package_path = f'{pipeline_name}.tar.gz'


def load_cookies(cookie_file, domain):
    cookiejar = http.cookiejar.MozillaCookieJar(cookie_file)
    cookiejar.load()
    for cookie in cookiejar:
        if cookie.domain == domain:
            cookies = f'{cookie.name}={cookie.value}'
            break
    return cookies

@dsl.pipeline(name=pipeline_name, description=description)
def pipeline(
    parameters: str,
    timestamp: str,
    data_train: str,
    data_val: str,
    data_test: str,
    network_config: str,
    data_config: str,
    model_prefix: str,
    log: str,
):

    train = train_op(
        parameters=parameters,
        timestamp=timestamp,
        data_train=data_train,
        data_val=data_val,
        data_test=data_test,
        network_config=network_config,
        data_config=data_config,
        model_prefix=model_prefix,
        log=log,
    )


if __name__ == '__main__':
    train_op = kfp.components.load_component_from_file('training/component.yaml')

    cookies = load_cookies(cookie_file='cookies.txt', domain='ml.cern.ch')
    
    client = kfp.Client(host='https://ml.cern.ch/pipeline', cookies=cookies)

    kfp.compiler.Compiler().compile(pipeline_func=pipeline, package_path=package_path)

    client.upload_pipeline(pipeline_package_path=package_path, pipeline_name=pipeline_name, description=description)

    experiment = client.create_experiment(name='jec-experiment', namespace='daniel-holmberg')

    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    
    name = config['name']

    parameters = json.dumps(config['parameters'])

    data_train = ' '.join(config['data']['train'])
    data_val = ' '.join(config['data']['val'])
    data_test = ' '.join(config['data']['test'])

    run = client.run_pipeline(
        pipeline_package_path=package_path,
        experiment_id=experiment.id,
        job_name=name,
        params={
            'parameters': parameters,
            'timestamp': timestamp,
            'data_train': data_train,
            'data_val': data_val,
            'data_test': data_test,
            'network_config': config['network_config'],
            'data_config': config['data_config'],
            'model_prefix': config['model_prefix'],
            'log': config['log'],
        }
    )

    print('Deployed', pipeline_name)
