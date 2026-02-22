"""Models for the coffeeshop project (contact messages etc.)."""

from django.db import models


class ContactMessage(models.Model):
    """Stores contact form submissions from site visitors."""

    name = models.CharField('Name', max_length=100)
    email = models.EmailField('Email')
    subject = models.CharField('Subject', max_length=200, blank=True)
    message = models.TextField('Message')
    created_at = models.DateTimeField('Sent at', auto_now_add=True)
    is_read = models.BooleanField('Read', default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'

    def __str__(self):
        return f'{self.name} — {self.subject or "(no subject)"} ({self.created_at:%Y-%m-%d %H:%M})'
