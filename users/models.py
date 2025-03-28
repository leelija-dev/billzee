from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    company_name = models.CharField(max_length=100, blank=True)
    company_email = models.EmailField(blank=True),
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    def __str__(self):
        return self.email

class Profile(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='profiles')
    is_active = models.BooleanField(default=False)
    company_name = models.CharField(max_length=100)
    company_email = models.EmailField()
    password = models.CharField(max_length=128, default='')
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)
    pin_or_zip = models.CharField(max_length=20, blank=True)
    gst_id = models.CharField(max_length=20, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'is_active'],
                condition=models.Q(is_active=True),
                name='unique_active_profile'
            )
        ]

    def save(self, *args, **kwargs):
        if self.is_active:
            # Set all other profiles of this user to inactive
            Profile.objects.filter(user=self.user).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company_name} - {self.user.username}"
