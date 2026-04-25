from kfp import dsl

@dsl.container_component
def scraping():
    return dsl.ContainerSpec(
        image="mohamediliasskaddar/e-commerce-agents:latest",
        command=["python", "agents/agent_coordinator.py"]
    )

@dsl.container_component
def ml_pipeline():
    return dsl.ContainerSpec(
        image="mohamediliasskaddar/e-commerce-pipeline:latest",
        command=["python", "pipeline/run_pipeline.py"]
    )

@dsl.pipeline(name="ecommerce-ml-pipeline")
def pipeline():
    s = scraping()
    m = ml_pipeline()
    m.after(s)
