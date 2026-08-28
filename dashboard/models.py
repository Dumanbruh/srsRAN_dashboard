from django.db import models


class Scenario(models.Model):
    """
    One row per scenario YAML file under dashboard/scenarios/ (is_builtin=True),
    synced by scenario_engine.sync_scenarios() — or a one-off scenario created
    from the "custom configuration" form (is_builtin=False, no backing file).
    """
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    definition = models.JSONField()  # parsed YAML: {parameters: {...}, steps: [...]}
    is_builtin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.slug


class ScenarioRun(models.Model):
    STATUS_IDLE = 'idle'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_STOPPED = 'stopped'
    STATUS_CHOICES = [
        (STATUS_IDLE, 'idle'),
        (STATUS_RUNNING, 'running'),
        (STATUS_COMPLETED, 'completed'),
        (STATUS_FAILED, 'failed'),
        (STATUS_STOPPED, 'stopped'),
    ]

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='runs')
    params = models.JSONField(default=dict)  # resolved parameters actually used for this run
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IDLE)
    current_step = models.IntegerField(null=True, blank=True)
    error = models.TextField(blank=True)
    stop_requested = models.BooleanField(default=False)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.scenario.slug} #{self.pk} ({self.status})'


class RunLog(models.Model):
    LEVEL_CHOICES = [('info', 'info'), ('warn', 'warn'), ('error', 'error')]

    run = models.ForeignKey(ScenarioRun, on_delete=models.CASCADE, related_name='logs')
    ts = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    step_index = models.IntegerField(null=True, blank=True)
    message = models.TextField()

    class Meta:
        ordering = ['id']
