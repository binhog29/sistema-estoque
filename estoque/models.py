from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# 1. O Equipamento (O que existe na empresa)
class Equipamento(models.Model):
    TIPO_CHOICES = [
        ('FIBRA', 'Fibra Óptica'),
        ('RADIO', 'Via Rádio'),
        ('FERRAMENTA', 'Ferramentas'),
    ]
    
    # Informações Básicas
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    
    # NOVOS CAMPOS (Especificações e Foto)
    especificacoes = models.TextField(blank=True, null=True, verbose_name="Especificações Técnicas")
    foto = models.ImageField(upload_to='equipamentos/', blank=True, null=True, verbose_name="Foto do Produto")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observações Gerais")

    # Controle de Quantidade
    quantidade = models.IntegerField(default=0, verbose_name="Estoque na Empresa")
    minimo = models.IntegerField(default=5, verbose_name="Alerta Mínimo")

    def __str__(self):
        return f"{self.nome} (Qtd: {self.quantidade})"

# 2. O Estoque do Técnico (O que está com ele/Dívida)
class EstoqueTecnico(models.Model):
    tecnico = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meu_estoque')
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE)
    quantidade = models.IntegerField(default=0, verbose_name="Qtd com Técnico")

    class Meta:
        unique_together = ('tecnico', 'equipamento') # Evita duplicidade
        verbose_name = "Carteira do Técnico"
        verbose_name_plural = "Carteiras dos Técnicos"

    def __str__(self):
        return f"{self.tecnico.username} tem {self.quantidade}x {self.equipamento.nome}"

# 3. A Movimentação (O registro seguro)
class Movimentacao(models.Model):
    TIPO_MOVIMENTO = [
        ('SAIDA', '🔴 Retirada (Vai para o Técnico)'),
        ('DEVOLUCAO', '🟢 Devolução (Volta para Empresa)'),
        ('BAIXA', '✅ Baixa em OS (Usado no Cliente)'),
    ]

    tecnico = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Técnico Responsável")
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_MOVIMENTO)
    quantidade = models.PositiveIntegerField()
    obs = models.CharField(max_length=100, blank=True, null=True, verbose_name="OBS / Nº da OS")
    data = models.DateTimeField(auto_now_add=True)
    autor_movimento = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='autor_log', verbose_name="Quem registrou (Secretária)")

    def save(self, *args, **kwargs):
        # Lógica automática de estoque
        carteira, created = EstoqueTecnico.objects.get_or_create(tecnico=self.tecnico, equipamento=self.equipamento)

        if self.pk is None: # Só executa se for registro novo
            if self.tipo == 'SAIDA':
                if self.equipamento.quantidade < self.quantidade:
                    raise ValidationError(f"Erro: Só tem {self.equipamento.quantidade} no estoque da empresa!")
                self.equipamento.quantidade -= self.quantidade
                carteira.quantidade += self.quantidade

            elif self.tipo == 'DEVOLUCAO':
                if carteira.quantidade < self.quantidade:
                    raise ValidationError(f"Erro: O técnico só tem {carteira.quantidade} em mãos!")
                self.equipamento.quantidade += self.quantidade
                carteira.quantidade -= self.quantidade

            elif self.tipo == 'BAIXA':
                if carteira.quantidade < self.quantidade:
                    raise ValidationError(f"Erro: O técnico tenta baixar mais do que tem!")
                carteira.quantidade -= self.quantidade
            
            self.equipamento.save()
            carteira.save()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Histórico de Movimentações"
    
    def __str__(self):
        return f"{self.tipo} - {self.equipamento.nome} ({self.quantidade})"
