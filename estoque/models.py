from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# ==============================================================================
# 1. O Equipamento (O que existe na empresa) - MANTIDO ORIGINAL
# ==============================================================================
class Equipamento(models.Model):
    TIPO_CHOICES = [
        ('FIBRA', 'Fibra Óptica'),
        ('RADIO', 'Via Rádio'),
        ('FERRAMENTA', 'Ferramentas'),
        ('TORRES', 'Equipamento para Torres'),
    ]
    
    # Informações Básicas
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    
    # NOVOS CAMPOS
    especificacoes = models.TextField(blank=True, null=True, verbose_name="Especificações Técnicas")
    foto = models.ImageField(upload_to='equipamentos/', blank=True, null=True, verbose_name="Foto do Produto")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observações Gerais")

    # Controle de Quantidade
    quantidade = models.IntegerField(default=0, verbose_name="Estoque na Empresa")
    minimo = models.IntegerField(default=5, verbose_name="Alerta Mínimo")

    def __str__(self):
        return f"{self.nome} (Qtd: {self.quantidade})"

# ==============================================================================
# 2. O Estoque do Técnico (O que está com ele/Dívida) - MANTIDO ORIGINAL
# ==============================================================================
class EstoqueTecnico(models.Model):
    tecnico = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meu_estoque')
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE)
    quantidade = models.IntegerField(default=0, verbose_name="Qtd com Técnico")

    class Meta:
        unique_together = ('tecnico', 'equipamento')
        verbose_name = "Carteira do Técnico (Saldo)"
        verbose_name_plural = "Carteiras dos Técnicos (Saldos)"

    def __str__(self):
        return f"{self.tecnico.username} tem {self.quantidade}x {self.equipamento.nome}"

# ==============================================================================
# 3. A Movimentação (O motor da automação) - MANTIDO ORIGINAL
# ==============================================================================
class Movimentacao(models.Model):
    TIPO_MOVIMENTO = [
        ('SAIDA', '🔴 Retirada (Sai do Estoque -> Vai pro Técnico)'),
        ('DEVOLUCAO', '🟢 Devolução (Sai do Técnico -> Volta pro Estoque)'),
        ('BAIXA', '✅ Baixa em OS (Sai do Técnico -> Cliente/Lixo)'),
    ]

    tecnico = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Técnico Responsável")
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_MOVIMENTO)
    quantidade = models.PositiveIntegerField()
    obs = models.CharField(max_length=100, blank=True, null=True, verbose_name="OBS / Nº da OS")
    data = models.DateTimeField(auto_now_add=True)
    autor_movimento = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='autor_log', verbose_name="Quem registrou")

    # --- NOVIDADE: A validação (clean) acontece ANTES de salvar ---
    def clean(self):
        # Se for edição (self.pk existe), não validamos saldo para evitar bloqueios antigos
        if self.pk is None:
            # Pega ou cria a carteira do técnico para conferir o saldo
            carteira, created = EstoqueTecnico.objects.get_or_create(tecnico=self.tecnico, equipamento=self.equipamento)

            # Validação 1: Empresa tem saldo para SAIDA?
            if self.tipo == 'SAIDA':
                if self.equipamento.quantidade < self.quantidade:
                    raise ValidationError(f"Estoque Insuficiente! A empresa só tem {self.equipamento.quantidade} unidades.")

            # Validação 2: Técnico tem saldo para DEVOLUCAO?
            elif self.tipo == 'DEVOLUCAO':
                if carteira.quantidade < self.quantidade:
                    raise ValidationError(f"Erro no Saldo! O técnico {self.tecnico.username} só tem {carteira.quantidade} em mãos.")

            # Validação 3: Técnico tem saldo para BAIXA?
            elif self.tipo == 'BAIXA':
                if carteira.quantidade < self.quantidade:
                    raise ValidationError(f"Não pode dar Baixa! O técnico tem apenas {carteira.quantidade} unidades deste item.")

    # --- AÇÃO: O save só executa se o clean passar ---
    def save(self, *args, **kwargs):
        if self.pk is None: 
            carteira, created = EstoqueTecnico.objects.get_or_create(tecnico=self.tecnico, equipamento=self.equipamento)

            # Executa a movimentação matemática
            if self.tipo == 'SAIDA':
                self.equipamento.quantidade -= self.quantidade
                carteira.quantidade += self.quantidade

            elif self.tipo == 'DEVOLUCAO':
                self.equipamento.quantidade += self.quantidade
                carteira.quantidade -= self.quantidade

            elif self.tipo == 'BAIXA':
                carteira.quantidade -= self.quantidade
            
            # Salva os saldos atualizados
            self.equipamento.save()
            carteira.save()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Registrar Movimentação"
        verbose_name_plural = "Registrar Movimentações"
    
    def __str__(self):
        return f"{self.tipo} - {self.equipamento.nome} ({self.quantidade})"

# ==============================================================================
# 4. SISTEMA DE LOTE (CARRINHO) - ATUALIZADO PARA FICAR IGUAL!
# ==============================================================================
# Agora as opções aqui são IDÊNTICAS às da Movimentação (Saída, Devolução e Baixa)

class OrdemMovimentacao(models.Model):
    tecnico = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Técnico Responsável")
    
    # ATUALIZAÇÃO AQUI: Adicionei a BAIXA e corrigi os textos para ficarem iguais
    tipo = models.CharField(max_length=20, choices=[
        ('SAIDA', '🔴 Retirada (Sai do Estoque -> Vai pro Técnico)'),
        ('DEVOLUCAO', '🟢 Devolução (Sai do Técnico -> Volta pro Estoque)'),
        ('BAIXA', '✅ Baixa em OS (Sai do Técnico -> Cliente/Lixo)'),
    ], default='SAIDA')
    
    data = models.DateTimeField(auto_now_add=True)
    obs = models.TextField(blank=True, null=True, verbose_name="Observação do Lote")

    # Trava de segurança para não lançar 2x se editar o pedido
    lancado = models.BooleanField(default=False, editable=False)

    def __str__(self):
        return f"Lote #{self.id} - {self.tecnico.username} ({self.get_tipo_display()})"

    class Meta:
        verbose_name = "🔴 Lançamento em Lote (Vários Itens)"
        verbose_name_plural = "🔴 Lançamentos em Lote (Vários Itens)"


class ItemOrdem(models.Model):
    ordem = models.ForeignKey(OrdemMovimentacao, on_delete=models.CASCADE)
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantidade}x {self.equipamento.nome}"
