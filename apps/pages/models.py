from django.db import models

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=50, blank=True, default="footer")

    def __str__(self):
        return self.email
