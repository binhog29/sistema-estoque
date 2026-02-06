from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Equipamento, EstoqueTecnico, Movimentacao, OrdemMovimentacao, ItemOrdem

# ==============================================================================
# 1. CONFIGURAÇÕES ANTIGAS (MANTIDAS EXATAMENTE IGUAIS)
# ==============================================================================

@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'quantidade', 'status_estoque')
    list_filter = ('tipo',)
    search_fields = ('nome',)

    def status_estoque(self, obj):
        if obj.quantidade <= obj.minimo:
            return "⚠️ BAIXO ESTOQUE"
        return "OK"

@admin.register(EstoqueTecnico)
class EstoqueTecnicoAdmin(admin.ModelAdmin):
    list_display = ('tecnico', 'equipamento', 'quantidade', 'alerta_pendencia')
    list_filter = ('tecnico', 'equipamento')
    
    def alerta_pendencia(self, obj):
        if obj.quantidade > 0:
            return "🔴 PENDENTE"
        return "🟢 ZERADO"

@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('data', 'tipo', 'tecnico', 'equipamento', 'quantidade', 'obs', 'autor_movimento')
    list_filter = ('tipo', 'tecnico', 'data')
    search_fields = ('obs', 'equipamento__nome', 'tecnico__username')
    
    # Salva automaticamente quem é a secretária/usuário logado
    def save_model(self, request, obj, form, change):
        if not obj.autor_movimento:
            obj.autor_movimento = request.user
        super().save_model(request, obj, form, change)


# ==============================================================================
# 2. NOVO SISTEMA DE LOTE (COM A TRAVA DE SEGURANÇA)
# ==============================================================================

class ItemOrdemInline(admin.TabularInline):
    model = ItemOrdem
    extra = 5 # Mostra 5 linhas vazias para preencher rápido
    autocomplete_fields = ['equipamento'] # Permite buscar digitando o nome

@admin.register(OrdemMovimentacao)
class OrdemMovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'tecnico', 'tipo', 'data', 'lancado')
    list_filter = ('tipo', 'data')
    search_fields = ('tecnico__username',)
    inlines = [ItemOrdemInline]
    
    # AQUI ESTÁ A PROTEÇÃO:
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        
        ordem = form.instance
        
        # Só executa a lógica se o lote ainda não foi processado (lancado=False)
        if not ordem.lancado:
            itens = ordem.itemordem_set.all()
            
            # --- FASE 1: TESTE DE SEGURANÇA (SIMULAÇÃO) ---
            # O sistema verifica item por item SE vai dar erro.
            # Se UM item falhar (ex: saldo insuficiente), ele cancela TUDO.
            for item in itens:
                # Cria uma movimentação "fantasma" na memória só para testar
                mov_teste = Movimentacao(
                    tecnico=ordem.tecnico,
                    equipamento=item.equipamento,
                    tipo=ordem.tipo,
                    quantidade=item.quantidade
                )
                try:
                    # Chama aquela validação que criamos no models.py (clean)
                    mov_teste.clean()
                except ValidationError as e:
                    # SE DER ERRO: Para tudo imediatamente!
                    # O usuário recebe um aviso e nada é gravado no estoque.
                    messages.error(request, f"❌ ERRO CANCELADO: O item '{item.equipamento.nome}' falhou. {e.message}")
                    return # Sai da função. O lote fica salvo, mas não processado.

            # --- FASE 2: EXECUÇÃO REAL (SÓ SE PASSOU NO TESTE) ---
            # Se chegou aqui, todos os itens são válidos. Pode gravar!
            n_criados = 0
            for item in itens:
                Movimentacao.objects.create(
                    tecnico=ordem.tecnico,
                    equipamento=item.equipamento,
                    tipo=ordem.tipo,
                    quantidade=item.quantidade,
                    obs=f"Lote #{ordem.id} | {ordem.obs or ''}",
                    autor_movimento=request.user
                )
                n_criados += 1
            
            # Marca como lançado (Check verde) e avisa sucesso
            ordem.lancado = True
            ordem.save()
            messages.success(request, f"✅ Sucesso! {n_criados} movimentações foram geradas e o estoque foi atualizado.")
