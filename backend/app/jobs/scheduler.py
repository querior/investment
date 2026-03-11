from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.jobs.macro_pipeline import run_macro_pipeline
from app.jobs.market_pipeline import run_market_pipeline

def start_scheduler():
  scheduler = BackgroundScheduler()

  scheduler.add_job(
      run_macro_pipeline,
      CronTrigger(hour=6, minute=0),  # ogni giorno alle 06:00
      id="macro_pipeline",
      replace_existing=True,
  )
  
  scheduler.add_job(
      run_market_pipeline,
      CronTrigger(hour=6, minute=0),
      id="market_pipeline",
      replace_existing=True
  )

  scheduler.start()