
from django.urls import path
from . import views
from . import perfil_cliente_views

app_name = 'loja'

urlpatterns = [
    path('', views.home, name='home'),
    path('catalogo/', views.catalogo, name='catalogo'),

    # Produtos
    path(
        'produto/<slug:slug>/',
        views.detalhe_produto,
        name='detalhe_produto'
    ),

    # Kits
    path(
        'kits/',
        views.kits_cliente,
        name='kits'
    ),
    path(
        'kit/<slug:slug>/',
        views.detalhe_kit_cliente,
        name='detalhe_kit'
    ),

    # Carrinho
    path('carrinho/', views.carrinho, name='carrinho'),
    path(
        'carrinho/adicionar/<int:produto_id>/',
        views.adicionar_carrinho,
        name='adicionar_carrinho'
    ),
    path(
        'carrinho/adicionar-kit/<int:kit_id>/',
        views.adicionar_kit_carrinho,
        name='adicionar_kit_carrinho'
    ),
    path(
        'carrinho/atualizar/<int:produto_id>/',
        views.atualizar_carrinho,
        name='atualizar_carrinho'
    ),
    path(
        'carrinho/atualizar-kit/<int:kit_id>/',
        views.atualizar_kit_carrinho,
        name='atualizar_kit_carrinho'
    ),
    path(
        'carrinho/remover/<int:produto_id>/',
        views.remover_carrinho,
        name='remover_carrinho'
    ),
    path(
        'carrinho/remover-kit/<int:kit_id>/',
        views.remover_kit_carrinho,
        name='remover_kit_carrinho'
    ),
    path(
        'carrinho/limpar/',
        views.limpar_carrinho,
        name='limpar_carrinho'
    ),

    # Finalizar pedido
    path(
        'finalizar-pedido/',
        views.finalizar_pedido,
        name='finalizar_pedido'
    ),

    # Cadastro e login
    path('cadastro/', views.cadastro_cliente, name='cadastro'),
    path('login/', views.login_cliente, name='login'),
    path('logout/', views.logout_cliente, name='logout'),

    # Perfil do cliente
    path(
        'minha-conta/',
        perfil_cliente_views.perfil_ver,
        name='perfil_ver'
    ),
    path(
        'minha-conta/editar/',
        perfil_cliente_views.perfil_editar,
        name='perfil_editar'
    ),

    # Pedidos
    path(
        'meus-pedidos/',
        views.meus_pedidos,
        name='meus_pedidos'
    ),
    path(
        'meus-pedidos/<int:encomenda_id>/cancelar/',
        views.cancelar_meu_pedido,
        name='cancelar_meu_pedido'
    ),
]
