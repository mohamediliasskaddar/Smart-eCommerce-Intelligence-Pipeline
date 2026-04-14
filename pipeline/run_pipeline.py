"""
pipeline/run_pipeline.py
MLOps/DevOps Pipeline Orchestrator
Runs all data processing, feature engineering, model training, and evaluation steps automatically
"""
import sys
import subprocess
import logging
import os
from pathlib import Path
from datetime import datetime

# Fix Windows Unicode encoding
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Setup logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s -- %(message)s',
    handlers=[
        logging.FileHandler(
            Path(__file__).parent.parent / "pipeline.log",
            encoding='utf-8'
        ),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# PIPELINE ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════

class PipelineOrchestrator:
    """Manages the complete ML pipeline execution"""

    def __init__(self):
        self.start_time = None
        self.steps = []
        self.failed_steps = []
        self.base_path = Path(__file__).parent.parent

    def log_start(self):
        self.start_time = datetime.now()
        logger.info("=" * 70)
        logger.info("[PIPELINE] STARTED")
        logger.info("=" * 70)

    def log_step(self, step_name: str, status: str):
        if status == "START":
            logger.info(f"[STEP] {step_name}... (starting)")
        elif status == "SUCCESS":
            logger.info(f"[STEP] {step_name}... (completed)")
        elif status == "ERROR":
            logger.error(f"[ERROR] {step_name}... (failed)")

    def log_end(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        logger.info("\n" + "=" * 70)
        if self.failed_steps:
            logger.error(f"[PIPELINE] COMPLETED WITH {len(self.failed_steps)} FAILURE(S):")
            for step in self.failed_steps:
                logger.error(f"  - {step}")
        else:
            logger.info("[PIPELINE] COMPLETED SUCCESSFULLY")
        logger.info(f"[TIME] Total elapsed: {elapsed:.1f}s")
        logger.info("=" * 70)

    def run_step(self, step_name: str, script_path: str):
        """Execute a pipeline step as a subprocess"""
        try:
            self.log_step(step_name, "START")
            full_path = self.base_path / script_path
            
            result = subprocess.run(
                [sys.executable, str(full_path)],
                cwd=str(self.base_path),
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=600
            )
            
            if result.returncode != 0:
                logger.error(f"Script stderr: {result.stderr[:500]}")
                raise Exception(f"Script failed with exit code {result.returncode}")
            
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logger.info(line)
            
            self.log_step(step_name, "SUCCESS")
            self.steps.append((step_name, "SUCCESS"))
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Step timed out (>600s)")
            self.log_step(step_name, "ERROR")
            self.steps.append((step_name, "FAILED"))
            self.failed_steps.append(step_name)
            return False
            
        except Exception as e:
            logger.error(f"Error details: {str(e)[:200]}")
            self.log_step(step_name, "ERROR")
            self.steps.append((step_name, "FAILED"))
            self.failed_steps.append(step_name)
            return False

    def run_all(self):
        """Execute complete pipeline"""
        self.log_start()

        # ── MODULE 1: DATA PROCESSING ─────────────────────────────────
        logger.info("\n--- MODULE 1: DATA INGESTION & PROCESSING ---")

        self.run_step(
            "Step 1.1: Preprocessing",
            "pipeline/steps/preprocess.py"
        )

        # ── MODULE 2: FEATURE ENGINEERING & ML PIPELINE ───────────────
        logger.info("\n--- MODULE 2: FEATURE ENGINEERING & MODEL TRAINING ---")

        self.run_step(
            "Step 2.1: Feature Engineering",
            "pipeline/steps/feature_engineering.py"
        )

        self.run_step(
            "Step 2.2: Model Training (XGBoost)",
            "pipeline/steps/train.py"
        )

        self.run_step(
            "Step 2.3: Evaluation & Reports",
            "pipeline/steps/evaluate.py"
        )

        # ── MODULE 3: ADVANCED ANALYTICS ──────────────────────────────
        logger.info("\n--- MODULE 3: ADVANCED ANALYTICS ---")

        self.run_step(
            "Step 3.1: Clustering Analysis",
            "pipeline/models/clustering.py"
        )

        self.run_step(
            "Step 3.2: Association Rules",
            "pipeline/models/association_rules.py"
        )

        self.log_end()

        # Return exit code
        return 0 if len(self.failed_steps) == 0 else 1


def run():
    """Main entry point for pipeline execution"""
    orchestrator = PipelineOrchestrator()
    exit_code = orchestrator.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    run()