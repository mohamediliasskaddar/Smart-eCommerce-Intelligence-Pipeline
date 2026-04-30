from kfp import dsl
from kfp.kubernetes import container_op

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


@dsl.pipeline(
    name="ecommerce-ml-pipeline",
    description="End-to-end ML pipeline for ecommerce intelligence with MinIO storage"
)
def pipeline():
    # Scraping task
    s = scraping()
    s.set_env_variable("MINIO_ENDPOINT", "minio.default.svc.cluster.local:9000")
    s.set_env_variable("MINIO_BUCKET", "smart-ecommerce")
    s.set_env_variable("MINIO_SECURE", "true")
    s.set_env_variable("DATA_PATH", "/app/data")
    
    # ML pipeline task
    m = ml_pipeline()
    m.set_env_variable("MINIO_ENDPOINT", "minio.default.svc.cluster.local:9000")
    m.set_env_variable("MINIO_BUCKET", "smart-ecommerce")
    m.set_env_variable("MINIO_SECURE", "true")
    m.set_env_variable("DATA_PATH", "/app/data")
    m.after(s)


from kfp import compiler

if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=pipeline,
        package_path="ecommerce_pipeline.yaml"
    )