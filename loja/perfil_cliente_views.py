
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import PerfilCliente
from .perfil_cliente_forms import PerfilClienteForm


@login_required(login_url='loja:login')
def perfil_ver(request):
    perfil = get_object_or_404(
        PerfilCliente,
        usuario=request.user
    )

    return render(
        request,
        'perfil_cliente.html',
        {
            'usuario': request.user,
            'perfil': perfil,
        }
    )


@login_required(login_url='loja:login')
def perfil_editar(request):
    perfil = get_object_or_404(
        PerfilCliente,
        usuario=request.user
    )

    form = PerfilClienteForm(
        request.POST or None,
        instance=request.user,
        perfil=perfil
    )

    if request.method == 'POST' and form.is_valid():
        usuario = form.save()

        update_session_auth_hash(request, usuario)

        messages.success(
            request,
            'Seu perfil foi atualizado com sucesso!'
        )

        return redirect('loja:perfil_ver')

    return render(
        request,
        'perfil_cliente_editar.html',
        {'form': form}
    )
