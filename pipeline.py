import kfp
from kfp import dsl
import http
import yaml
import json
from datetime import datetime

timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
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
    timestamp: str,
    model_name: str,
):

    train = train_op(
        timestamp=timestamp,
    )

    serve = serve_op(
        model_path=train.outputs['output_path'],
        model_name=model_name,
    )

if __name__ == '__main__':
    train_op = kfp.components.load_component_from_file('training/component.yaml')
    serve_op = kfp.components.load_component_from_file('serving/component.yaml')

    cookies = load_cookies(cookie_file='cookies.txt', domain='ml-staging.cern.ch')
    
    client = kfp.Client(host='https://ml-staging.cern.ch/pipeline', cookies=cookies)

    kfp.compiler.Compiler().compile(pipeline_func=pipeline, package_path=package_path)

    client.upload_pipeline(pipeline_package_path=package_path, pipeline_name=pipeline_name, description=description)

    experiment = client.create_experiment(name='jec-experiment', namespace='dholmber')

    run = client.run_pipeline(
        pipeline_package_path=package_path,
        experiment_id=experiment.id,
        job_name='jec-trial',
        params={
            'timestamp': timestamp,
            'model_name': f'pfn-{timestamp}'
        }
    )

    print('Deployed', pipeline_name)
