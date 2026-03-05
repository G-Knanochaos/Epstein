from django.db import models


class Celebrity(models.Model):
    full_name = models.CharField(max_length=200)
    description = models.CharField(max_length=600, blank=True)
    extract = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    wikipedia_url = models.URLField(max_length=500, blank=True)
    wikipedia_slug = models.CharField(max_length=200, blank=True)
    epstein_mentions = models.IntegerField(default=0)

    class Meta:
        ordering = ['-epstein_mentions']
        verbose_name_plural = 'celebrities'

    def __str__(self):
        return f"{self.full_name} ({self.epstein_mentions} mentions)"
