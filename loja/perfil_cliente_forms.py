
from django import forms
from django.contrib.auth.models import User

from .models import PerfilCliente


class PerfilClienteForm(forms.ModelForm):

    telefone = forms.CharField(
        label='Telefone',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'input-control',
            'placeholder': '(00) 00000-0000'
        })
    )

    nova_senha = forms.CharField(
        label='Nova Senha (deixe em branco para não alterar)',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'input-control',
            'placeholder': 'Digite uma nova senha'
        })
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
        ]

        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'username': 'Nome de Usuário',
            'email': 'E-mail',
        }

        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'input-control'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'input-control'
            }),
            'username': forms.TextInput(attrs={
                'class': 'input-control'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.perfil = kwargs.pop('perfil')
        super().__init__(*args, **kwargs)

        self.fields['telefone'].initial = self.perfil.telefone

    def clean_username(self):
        username = self.cleaned_data['username'].strip()

        usuarios = User.objects.filter(
            username__iexact=username
        ).exclude(pk=self.instance.pk)

        if usuarios.exists():
            raise forms.ValidationError(
                'Este nome de usuário já está sendo utilizado.'
            )

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        usuarios = User.objects.filter(
            email__iexact=email
        ).exclude(pk=self.instance.pk)

        if email and usuarios.exists():
            raise forms.ValidationError(
                'Este e-mail já está sendo utilizado.'
            )

        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)

        nova_senha = self.cleaned_data.get('nova_senha')

        if nova_senha:
            usuario.set_password(nova_senha)

        if commit:
            usuario.save()

            self.perfil.telefone = self.cleaned_data['telefone']
            self.perfil.save()

        return usuario
