
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import quote

from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.db.models import Sum, Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.decorators.http import require_POST

from categorias.models import Categoria
from produtos.models import Produto
from kits.models import Kit
from encomendas.models import (
    Encomenda,
    ItemEncomendaProduto,
    ItemEncomendaKit,
)

from .forms import CadastroClienteForm
from .models import PerfilCliente


# ============================================================
# FUNÇÕES AUXILIARES DO CARRINHO
# ============================================================

def _chave_kit(kit_id):
    return f'kit_{kit_id}'


def _obter_quantidade(valor):
    try:
        quantidade = int(valor)
    except (TypeError, ValueError):
        return 0

    return quantidade


# ============================================================
# PÁGINA INICIAL
# ============================================================

def home(request):
    categorias = Categoria.objects.filter(ativo=True)

    context = {
        'categorias': categorias
    }

    return render(request, 'home.html', context)


# ============================================================
# CATÁLOGO DE PRODUTOS
# ============================================================

def catalogo(request):
    categorias = Categoria.objects.filter(ativo=True)
    produtos = Produto.objects.filter(
        ativo=True
    ).select_related('categoria')

    categoria_id = request.GET.get('categoria')
    ordem = request.GET.get('ordem', 'vendidos')
    busca = request.GET.get('q', '').strip()

    if busca:
        produtos = produtos.filter(nome__icontains=busca)

    if categoria_id and categoria_id.isdigit():
        produtos = produtos.filter(categoria_id=categoria_id)

    if ordem == 'menor':
        produtos = produtos.order_by('preco', 'nome')

    elif ordem == 'maior':
        produtos = produtos.order_by('-preco', 'nome')

    else:
        produtos = produtos.annotate(
            total_vendido=Sum(
                'itemencomendaproduto__quantidade',
                filter=Q(
                    itemencomendaproduto__encomenda__status='Concluida'
                ),
                default=0
            )
        ).order_by('-total_vendido', 'nome')

    context = {
        'categorias': categorias,
        'produtos': produtos,
        'categoria_ativa': int(categoria_id)
        if categoria_id and categoria_id.isdigit()
        else None,
        'ordem_ativa': ordem,
        'busca': busca,
    }

    return render(request, 'catalogo.html', context)


# ============================================================
# DETALHES DO PRODUTO
# ============================================================

def detalhe_produto(request, slug):
    produto = get_object_or_404(
        Produto.objects.select_related('categoria'),
        slug=slug,
        ativo=True
    )

    return render(
        request,
        'produto_detalhe.html',
        {'produto': produto}
    )


# ============================================================
# KITS DISPONÍVEIS PARA O CLIENTE
# ============================================================

def kits_cliente(request):
    kits = Kit.objects.filter(
        ativo=True
    ).prefetch_related('produtos')

    context = {
        'kits': kits,
    }

    return render(request, 'kits_cliente.html', context)


# ============================================================
# DETALHES DE UM KIT
# ============================================================

def detalhe_kit_cliente(request, slug):
    kit = get_object_or_404(
        Kit.objects.prefetch_related('produtos'),
        slug=slug,
        ativo=True
    )

    context = {
        'kit': kit,
    }

    return render(request, 'kit_detalhe_cliente.html', context)


# ============================================================
# ADICIONAR PRODUTO AO CARRINHO
# ============================================================

@require_POST
def adicionar_carrinho(request, produto_id):
    produto = get_object_or_404(
        Produto,
        id=produto_id,
        ativo=True
    )

    quantidade = _obter_quantidade(
        request.POST.get('quantidade', 1)
    )

    if quantidade < 1:
        messages.error(request, 'Informe uma quantidade válida.')
        return redirect(
            'loja:detalhe_produto',
            slug=produto.slug
        )

    carrinho = request.session.get('carrinho', {})
    produto_id_str = str(produto.id)

    quantidade_atual = _obter_quantidade(
        carrinho.get(produto_id_str, 0)
    )

    if quantidade_atual + quantidade > produto.estoque:
        messages.error(
            request,
            'A quantidade solicitada ultrapassa o estoque disponível.'
        )

        return redirect(
            'loja:detalhe_produto',
            slug=produto.slug
        )

    carrinho[produto_id_str] = quantidade_atual + quantidade

    request.session['carrinho'] = carrinho
    request.session.modified = True

    messages.success(
        request,
        f'{produto.nome} foi adicionado ao carrinho!'
    )

    return redirect(
        'loja:detalhe_produto',
        slug=produto.slug
    )


# ============================================================
# ADICIONAR KIT AO MESMO CARRINHO DOS PRODUTOS
# ============================================================

@require_POST
def adicionar_kit_carrinho(request, kit_id):
    kit = get_object_or_404(
        Kit,
        id=kit_id,
        ativo=True
    )

    quantidade = _obter_quantidade(
        request.POST.get('quantidade', 1)
    )

    if quantidade < 1:
        messages.error(request, 'Informe uma quantidade válida.')

        return redirect(
            'loja:detalhe_kit',
            slug=kit.slug
        )

    carrinho = request.session.get('carrinho', {})
    kit_id_str = _chave_kit(kit.id)

    quantidade_atual = _obter_quantidade(
        carrinho.get(kit_id_str, 0)
    )

    carrinho[kit_id_str] = quantidade_atual + quantidade

    request.session['carrinho'] = carrinho
    request.session.modified = True

    messages.success(
        request,
        f'{kit.nome} foi adicionado ao carrinho!'
    )

    return redirect(
        'loja:detalhe_kit',
        slug=kit.slug
    )


# ============================================================
# EXIBIR CARRINHO COM PRODUTOS E KITS
# ============================================================

def carrinho(request):
    carrinho_sessao = request.session.get('carrinho', {})

    itens = []
    total = Decimal('0.00')

    ids_produtos = []
    ids_kits = []

    for chave, quantidade in carrinho_sessao.items():
        if chave.startswith('kit_'):
            try:
                ids_kits.append(int(chave.replace('kit_', '', 1)))
            except ValueError:
                continue
        else:
            try:
                ids_produtos.append(int(chave))
            except (ValueError, AttributeError):
                continue

    produtos = Produto.objects.filter(
        id__in=ids_produtos,
        ativo=True
    )

    kits = Kit.objects.filter(
        id__in=ids_kits,
        ativo=True
    )

    for produto in produtos:
        quantidade = _obter_quantidade(
            carrinho_sessao.get(str(produto.id), 0)
        )

        if quantidade < 1:
            continue

        subtotal = produto.preco * quantidade

        itens.append({
            'tipo': 'produto',
            'id': produto.id,
            'nome': produto.nome,
            'preco': produto.preco,
            'imagem': produto.imagem,
            'quantidade': quantidade,
            'subtotal': subtotal,
            'estoque': produto.estoque,
        })

        total += subtotal

    for kit in kits:
        quantidade = _obter_quantidade(
            carrinho_sessao.get(_chave_kit(kit.id), 0)
        )

        if quantidade < 1:
            continue

        subtotal = kit.preco * quantidade

        itens.append({
            'tipo': 'kit',
            'id': kit.id,
            'nome': kit.nome,
            'preco': kit.preco,
            'imagem': kit.imagem,
            'quantidade': quantidade,
            'subtotal': subtotal,
            'estoque': None,
        })

        total += subtotal

    context = {
        'itens': itens,
        'total': total,
    }

    return render(request, 'carrinho.html', context)


# ============================================================
# ATUALIZAR QUANTIDADE DE PRODUTO
# ============================================================

@require_POST
def atualizar_carrinho(request, produto_id):
    carrinho_sessao = request.session.get('carrinho', {})
    produto_id_str = str(produto_id)

    if produto_id_str not in carrinho_sessao:
        messages.error(
            request,
            'Produto não encontrado no carrinho.'
        )
        return redirect('loja:carrinho')

    produto = get_object_or_404(
        Produto,
        id=produto_id,
        ativo=True
    )

    quantidade = _obter_quantidade(
        request.POST.get('quantidade', 1)
    )

    if quantidade < 1:
        messages.error(request, 'Informe uma quantidade válida.')
        return redirect('loja:carrinho')

    if quantidade > produto.estoque:
        messages.error(
            request,
            'A quantidade solicitada ultrapassa o estoque disponível.'
        )
        return redirect('loja:carrinho')

    carrinho_sessao[produto_id_str] = quantidade

    request.session['carrinho'] = carrinho_sessao
    request.session.modified = True

    messages.success(request, 'Quantidade atualizada.')

    return redirect('loja:carrinho')


# ============================================================
# ATUALIZAR QUANTIDADE DE KIT
# ============================================================

@require_POST
def atualizar_kit_carrinho(request, kit_id):
    carrinho_sessao = request.session.get('carrinho', {})
    kit_id_str = _chave_kit(kit_id)

    if kit_id_str not in carrinho_sessao:
        messages.error(
            request,
            'Kit não encontrado no carrinho.'
        )
        return redirect('loja:carrinho')

    kit = get_object_or_404(
        Kit,
        id=kit_id,
        ativo=True
    )

    quantidade = _obter_quantidade(
        request.POST.get('quantidade', 1)
    )

    if quantidade < 1:
        messages.error(request, 'Informe uma quantidade válida.')
        return redirect('loja:carrinho')

    carrinho_sessao[kit_id_str] = quantidade

    request.session['carrinho'] = carrinho_sessao
    request.session.modified = True

    messages.success(
        request,
        f'Quantidade do kit {kit.nome} atualizada.'
    )

    return redirect('loja:carrinho')


# ============================================================
# REMOVER PRODUTO DO CARRINHO
# ============================================================

@require_POST
def remover_carrinho(request, produto_id):
    carrinho_sessao = request.session.get('carrinho', {})
    produto_id_str = str(produto_id)

    if produto_id_str in carrinho_sessao:
        del carrinho_sessao[produto_id_str]

        request.session['carrinho'] = carrinho_sessao
        request.session.modified = True

        messages.success(
            request,
            'Produto removido do carrinho.'
        )

    return redirect('loja:carrinho')


# ============================================================
# REMOVER KIT DO CARRINHO
# ============================================================

@require_POST
def remover_kit_carrinho(request, kit_id):
    carrinho_sessao = request.session.get('carrinho', {})
    kit_id_str = _chave_kit(kit_id)

    if kit_id_str in carrinho_sessao:
        del carrinho_sessao[kit_id_str]

        request.session['carrinho'] = carrinho_sessao
        request.session.modified = True

        messages.success(
            request,
            'Kit removido do carrinho.'
        )

    return redirect('loja:carrinho')


# ============================================================
# ESVAZIAR CARRINHO
# ============================================================

@require_POST
def limpar_carrinho(request):
    request.session['carrinho'] = {}
    request.session.modified = True

    messages.success(request, 'Carrinho esvaziado.')

    return redirect('loja:carrinho')


# ============================================================
# CADASTRO DO CLIENTE
# ============================================================

def cadastro_cliente(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil_cliente'):
            return redirect('loja:carrinho')

        return redirect('loja:home')

    form = CadastroClienteForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                usuario = form.save(commit=False)
                usuario.save()

                PerfilCliente.objects.create(
                    usuario=usuario,
                    telefone=form.cleaned_data['telefone']
                )

            login(request, usuario)

            messages.success(
                request,
                'Cadastro realizado com sucesso! Confira seu carrinho.'
            )

            return redirect('loja:carrinho')

        except Exception:
            messages.error(
                request,
                'Não foi possível concluir seu cadastro. Tente novamente.'
            )

    return render(
        request,
        'cadastro.html',
        {'form': form}
    )


# ============================================================
# LOGIN DO CLIENTE
# ============================================================

def login_cliente(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil_cliente'):
            return redirect('loja:carrinho')

        return redirect('loja:home')

    if request.method == 'POST':
        email = request.POST.get(
            'username',
            ''
        ).strip().lower()

        senha = request.POST.get('password', '')

        usuario = authenticate(
            request,
            username=email,
            password=senha
        )

        if usuario is not None and hasattr(
            usuario,
            'perfil_cliente'
        ):
            login(request, usuario)

            if request.POST.get('lembrar'):
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)

            messages.success(
                request,
                'Login realizado com sucesso!'
            )

            return redirect('loja:carrinho')

        messages.error(
            request,
            'E-mail ou senha incorretos.'
        )

    return render(request, 'login.html')


# ============================================================
# LOGOUT DO CLIENTE
# ============================================================

def logout_cliente(request):
    if request.user.is_authenticated and hasattr(
        request.user,
        'perfil_cliente'
    ):
        logout(request)

    return redirect('loja:home')


# ============================================================
# FINALIZAR PEDIDO COM PRODUTOS E KITS
# ============================================================

def finalizar_pedido(request):
    if not request.user.is_authenticated:
        return redirect('loja:login')

    if not hasattr(request.user, 'perfil_cliente'):
        messages.error(
            request,
            'Somente clientes podem finalizar pedidos.'
        )
        return redirect('loja:home')

    carrinho = request.session.get('carrinho', {})

    if not carrinho:
        messages.warning(
            request,
            'Seu carrinho está vazio.'
        )
        return redirect('loja:carrinho')

    def obter_itens():
        itens = []
        total = Decimal('0.00')

        ids_produtos = []
        ids_kits = []

        for chave in carrinho.keys():
            if chave.startswith('kit_'):
                try:
                    ids_kits.append(
                        int(chave.replace('kit_', '', 1))
                    )
                except ValueError:
                    raise ValueError(
                        'Existe um item inválido no carrinho.'
                    )
            else:
                try:
                    ids_produtos.append(int(chave))
                except (ValueError, AttributeError):
                    raise ValueError(
                        'Existe um item inválido no carrinho.'
                    )

        produtos = Produto.objects.filter(
            id__in=ids_produtos,
            ativo=True
        )

        kits = Kit.objects.filter(
            id__in=ids_kits,
            ativo=True
        )

        produtos_encontrados = {
            produto.id: produto
            for produto in produtos
        }

        kits_encontrados = {
            kit.id: kit
            for kit in kits
        }

        for produto_id in ids_produtos:
            produto = produtos_encontrados.get(produto_id)

            if produto is None:
                raise ValueError(
                    'Um ou mais produtos não estão disponíveis.'
                )

            quantidade = _obter_quantidade(
                carrinho.get(str(produto_id), 0)
            )

            if quantidade < 1 or quantidade > produto.estoque:
                raise ValueError(
                    f'Estoque insuficiente para {produto.nome}.'
                )

            subtotal = produto.preco * quantidade

            itens.append({
                'tipo': 'produto',
                'produto': produto,
                'kit': None,
                'quantidade': quantidade,
                'subtotal': subtotal,
            })

            total += subtotal

        for kit_id in ids_kits:
            kit = kits_encontrados.get(kit_id)

            if kit is None:
                raise ValueError(
                    'Um ou mais kits não estão disponíveis.'
                )

            quantidade = _obter_quantidade(
                carrinho.get(_chave_kit(kit_id), 0)
            )

            if quantidade < 1:
                raise ValueError(
                    f'Quantidade inválida para o kit {kit.nome}.'
                )

            subtotal = kit.preco * quantidade

            itens.append({
                'tipo': 'kit',
                'produto': None,
                'kit': kit,
                'quantidade': quantidade,
                'subtotal': subtotal,
            })

            total += subtotal

        if not itens:
            raise ValueError(
                'Seu carrinho não possui itens disponíveis.'
            )

        return itens, total

    try:
        itens, total = obter_itens()

    except ValueError as erro:
        messages.error(request, str(erro))
        return redirect('loja:carrinho')

    if request.method == 'POST':
        try:
            data_entrega = date.fromisoformat(
                request.POST.get('data_entrega', '')
            )

            data_minima = (
                timezone.localdate() + timedelta(days=1)
            )

            if data_entrega < data_minima:
                messages.error(
                    request,
                    'Escolha uma data a partir de amanhã.'
                )

            else:
                with transaction.atomic():
                    itens, total = obter_itens()

                    encomenda = Encomenda(
                        cliente=request.user,
                        data_entrega=data_entrega,
                        status='Pendente',
                        valor_total=total
                    )

                    encomenda.full_clean()
                    encomenda.save()

                    for item in itens:
                        if item['tipo'] == 'produto':
                            ItemEncomendaProduto.objects.create(
                                encomenda=encomenda,
                                produto=item['produto'],
                                quantidade=item['quantidade']
                            )

                        elif item['tipo'] == 'kit':
                            ItemEncomendaKit.objects.create(
                                encomenda=encomenda,
                                kit=item['kit'],
                                quantidade=item['quantidade']
                            )

                mensagem = (
                    f'Olá! Gostaria de confirmar minha encomenda '
                    f'#{encomenda.id}.\n\n'
                    f'Cliente: {request.user.get_full_name()}\n'
                    f'Data de entrega: '
                    f'{data_entrega.strftime("%d/%m/%Y")}\n\n'
                    f'Itens da encomenda:\n'
                )

                for item in itens:
                    if item['tipo'] == 'produto':
                        nome_item = item['produto'].nome
                    else:
                        nome_item = item['kit'].nome

                    mensagem += (
                        f'- {nome_item} '
                        f'(Quantidade: {item["quantidade"]}) '
                        f'- R$ {item["subtotal"]:.2f}\n'
                    )

                mensagem += f'\nTotal: R$ {total:.2f}'

                request.session['carrinho'] = {}
                request.session.modified = True

                return redirect(
                    'https://wa.me/5565998047155?text='
                    + quote(mensagem)
                )

        except (ValueError, TypeError):
            messages.error(
                request,
                'Informe uma data de entrega válida.'
            )

        except ValidationError as erro:
            messages.error(
                request,
                f'Data de entrega inválida: {erro.messages}'
            )

    context = {
        'itens': itens,
        'total': total,
        'data_minima': (
            timezone.localdate() + timedelta(days=1)
        ).isoformat(),
    }

    return render(
        request,
        'confirmar_pedido.html',
        context
    )


# ============================================================
# MEUS PEDIDOS
# ============================================================

def meus_pedidos(request):
    if not request.user.is_authenticated:
        return redirect('loja:login')

    if not hasattr(request.user, 'perfil_cliente'):
        messages.error(
            request,
            'Somente clientes podem acessar seus pedidos.'
        )
        return redirect('loja:home')

    encomendas = Encomenda.objects.filter(
        cliente=request.user
    ).prefetch_related(
        'itemencomendaproduto_set__produto',
        'itemencomendakit_set__kit'
    ).order_by('-data_criacao')

    context = {
        'encomendas': encomendas
    }

    return render(
        request,
        'meus_pedidos.html',
        context
    )


# ============================================================
# CANCELAR PEDIDO
# ============================================================

@require_POST
def cancelar_meu_pedido(request, encomenda_id):
    if not request.user.is_authenticated:
        return redirect('loja:login')

    if not hasattr(request.user, 'perfil_cliente'):
        messages.error(
            request,
            'Somente clientes podem cancelar pedidos.'
        )
        return redirect('loja:home')

    encomenda = get_object_or_404(
        Encomenda,
        id=encomenda_id,
        cliente=request.user
    )

    if encomenda.status != 'Pendente':
        messages.error(
            request,
            'Somente pedidos pendentes podem ser cancelados.'
        )
        return redirect('loja:meus_pedidos')

    encomenda.status = 'Cancelada'
    encomenda.save(update_fields=['status'])

    messages.success(
        request,
        f'Pedido #{encomenda.id} cancelado com sucesso.'
    )

    return redirect('loja:meus_pedidos')
