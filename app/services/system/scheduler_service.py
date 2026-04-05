from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


def init_scheduler(app):
    """Initialize APScheduler with configured jobs."""
    from ...extensions import redis_client

    def daily_topic_generation():
        """Scheduled job: generate topics and send to Telegram."""
        with app.app_context():
            from ..content.topic_service import generate_topics
            from ..distribution.telegram_service import send_topic_choices
            try:
                topics = generate_topics()
                if topics:
                    send_topic_choices(topics)
                    print(f'[Scheduler] Generated {len(topics)} topics and sent to Telegram')
            except Exception as e:
                print(f'[Scheduler] Topic generation failed: {e}')

    def cleanup_old_topics():
        """Delete unselected recommended topics older than 30 days."""
        with app.app_context():
            from datetime import date, timedelta
            from ...extensions import db
            from ...models.topic import RecommendedTopic
            cutoff = date.today() - timedelta(days=30)
            old_topics = RecommendedTopic.query.filter(
                RecommendedTopic.is_selected == False,
                RecommendedTopic.batch_date < cutoff,
            ).all()
            count = len(old_topics)
            if count > 0:
                for t in old_topics:
                    db.session.delete(t)
                db.session.commit()
                print(f'[Scheduler] Cleaned up {count} old unselected topics (before {cutoff})')

    # Get schedule time from settings
    schedule_time = redis_client.hget('settings:general', 'schedule_time') or '09:00'
    hour, minute = schedule_time.split(':')

    scheduler.add_job(
        daily_topic_generation,
        'cron',
        hour=int(hour),
        minute=int(minute),
        id='daily_topic_generation',
        replace_existing=True,
    )

    # Cleanup old unselected topics daily at 03:00
    scheduler.add_job(
        cleanup_old_topics,
        'cron',
        hour=3,
        minute=0,
        id='cleanup_old_topics',
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()
        print(f'[Scheduler] Started. Daily topic generation at {schedule_time}')
