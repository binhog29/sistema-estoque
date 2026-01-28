from django.contrib import admin
from .models import Equipamento, EstoqueTecnico, Movimentacao

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
    
    # Salva automaticamente quem é a secretária logada
    def save_model(self, request, obj, form, change):
        if not obj.autor_movimento:
            obj.autor_movimento = request.user
        super().save_model(request, obj, form, change)
