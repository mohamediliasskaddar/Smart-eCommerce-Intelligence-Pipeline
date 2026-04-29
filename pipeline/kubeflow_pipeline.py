#pipeline/kubeflow_pipeline.py
# from kfp import dsl

# @dsl.container_component
# def scraping():
#     return dsl.ContainerSpec(
#         image="mohamediliasskaddar/e-commerce-agents:latest",
#         command=["python", "agents/agent_coordinator.py"]
#     )

# @dsl.container_component
# def ml_pipeline():
#     return dsl.ContainerSpec(
#         image="mohamediliasskaddar/e-commerce-pipeline:latest",
#         command=["python", "pipeline/run_pipeline.py"]
#     )

# @dsl.pipeline(name="ecommerce-ml-pipeline")
# def pipeline():
#     s = scraping()
#     m = ml_pipeline()
#     m.after(s)
from kfp import dsl

@dsl.component(
    base_image="mohamediliasskaddar/e-commerce-agents:latest"
)
def scraping():
    import subprocess
    subprocess.run(["python", "agents/agent_coordinator.py"], check=True)


@dsl.component(
    base_image="mohamediliasskaddar/e-commerce-pipeline:latest"
)
def ml_pipeline():
    import subprocess
    subprocess.run(["python", "pipeline/run_pipeline.py"], check=True)


@dsl.pipeline(name="ecommerce-ml-pipeline")
def pipeline():
    s = scraping()
    m = ml_pipeline()
    m.after(s)

from kfp import compiler

if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=pipeline,
        package_path="ecommerce_pipeline.yaml"
    )