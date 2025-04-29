// Variáveis globais
const sheetName = 'Sheet1';

/**
 * Configura o script com o ID da planilha ativa
 */
function initialSetup() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getActiveSheet();
  
  // Renomear a primeira aba se necessário
  if (sheet.getName() !== "Sheet1") {
    sheet.setName("Sheet1");
  }
  
  // Definir cabeçalhos (agora com Recepção)
  sheet.getRange("A1:F1").setValues([["Recepção", "Timestamp", "Email", "Atendimento", "Recomendação", "Comentário"]]);
  sheet.getRange("A1:F1").setFontWeight("bold");
  sheet.setFrozenRows(1);
  
  // Ajustar largura das colunas
  sheet.setColumnWidth(1, 180); // Recepção
  sheet.setColumnWidth(2, 180); // Timestamp
  sheet.setColumnWidth(3, 200); // Email
  sheet.setColumnWidth(4, 120); // Atendimento
  sheet.setColumnWidth(5, 120); // Recomendação
  sheet.setColumnWidth(6, 400); // Comentário
  
  // Formatar como tabela
  var range = sheet.getDataRange();
  range.setBorder(true, true, true, true, true, true);
  
  // Salvar ID da planilha nas propriedades do script
  var scriptProperties = PropertiesService.getScriptProperties();
  scriptProperties.setProperty('spreadsheetId', ss.getId());
  
  // Mensagem de confirmação
  SpreadsheetApp.getUi().alert("Configuração inicial concluída com sucesso!");
  
  return 'Setup concluído com sucesso! ID da planilha: ' + ss.getId();
}

/**
 * Método doGet para processar solicitações GET
 */
function doGet(e) {
  // Se temos parâmetros, processa como uma submissão
  if (e && e.parameter && Object.keys(e.parameter).length > 0) {
    try {
      // Adquirir um bloqueio para evitar conflitos de acesso concorrente
      const lock = LockService.getScriptLock();
      lock.tryLock(10000); // Tenta adquirir lock por 10 segundos
      
      // Obter os parâmetros
      var data = e.parameter;
      
      // Validar campos obrigatórios
      if (!data.recepcao || !data.atendimento || !data.recomendacao) {
        return ContentService.createTextOutput(JSON.stringify({
          success: false,
          error: "Campos obrigatórios não preenchidos."
        }))
        .setMimeType(ContentService.MimeType.JSON)
        .setHeader('Access-Control-Allow-Origin', '*')
        .setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        .setHeader('Access-Control-Allow-Headers', 'Content-Type');
      }
      
      // Obter o ID da planilha das propriedades do script
      const scriptProperties = PropertiesService.getScriptProperties();
      const spreadsheetId = scriptProperties.getProperty('spreadsheetId');
      
      if (!spreadsheetId) {
        throw new Error('ID da planilha não encontrado. Execute a função initialSetup primeiro.');
      }
      
      // Acessar a planilha ativa
      var ss = SpreadsheetApp.openById(spreadsheetId);
      var sheet = ss.getSheetByName("Sheet1");
      
      if (!sheet) {
        throw new Error(`Planilha \"Sheet1\" não encontrada.`);
      }
      
      // Criar o registro com data e hora atual
      var timestamp = new Date();
      var email = ""; // Email não é mais coletado
      var atendimento = data.atendimento;
      var recomendacao = data.recomendacao;
      var comentario = data.comentario || ""; // Comentário é opcional
      var recepcao = data.recepcao || "";
      
      // Adicionar o registro à planilha (Recepção é a primeira coluna)
      sheet.appendRow([recepcao, timestamp, email, atendimento, recomendacao, comentario]);
      
      // Retornar resposta de sucesso
      return HtmlService.createHtmlOutput("Sucesso! Sua avaliação foi registrada.");
      
    } catch (error) {
      // Registrar o erro para depuração
      console.error("Erro ao processar submissão: " + error.toString());
      
      // Retornar resposta de erro
      return HtmlService.createHtmlOutput("Erro: " + error.toString());
    } finally {
      // Liberar o bloqueio se existir
      const lock = LockService.getScriptLock();
      if (lock.hasLock()) {
        lock.releaseLock();
      }
    }
  } else {
    // Resposta padrão quando não há parâmetros (apenas teste)
    return ContentService.createTextOutput('O serviço está funcionando. Este endpoint aceita solicitações GET com parâmetros ou POST.')
    .setHeader('Access-Control-Allow-Origin', '*')
    .setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    .setHeader('Access-Control-Allow-Headers', 'Content-Type');
  }
}

/**
 * Manipula solicitações POST do formulário HTML
 */
function doPost(e) {
  try {
    // Adquirir um bloqueio para evitar conflitos de acesso concorrente
    const lock = LockService.getScriptLock();
    lock.tryLock(10000); // Tenta adquirir lock por 10 segundos
    
    // Verificar se os dados foram recebidos
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(JSON.stringify({
        success: false,
        error: "Dados não recebidos."
      }))
      .setMimeType(ContentService.MimeType.JSON)
      .setHeader('Access-Control-Allow-Origin', '*')
      .setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
      .setHeader('Access-Control-Allow-Headers', 'Content-Type');
    }
    
    // Obter e analisar os dados enviados
    var data = JSON.parse(e.postData.contents);
    
    // Validar campos obrigatórios
    if (!data.recepcao || !data.atendimento || !data.recomendacao) {
      return ContentService.createTextOutput(JSON.stringify({
        success: false,
        error: "Campos obrigatórios não preenchidos."
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Obter o ID da planilha das propriedades do script
    const scriptProperties = PropertiesService.getScriptProperties();
    const spreadsheetId = scriptProperties.getProperty('spreadsheetId');
    
    if (!spreadsheetId) {
      throw new Error('ID da planilha não encontrado. Execute a função initialSetup primeiro.');
    }
    
    // Acessar a planilha ativa
    var ss = SpreadsheetApp.openById(spreadsheetId);
    var sheet = ss.getSheetByName("Sheet1");
    
    if (!sheet) {
      throw new Error(`Planilha \"Sheet1\" não encontrada.`);
    }
    
    // Criar o registro com data e hora atual
    var timestamp = new Date();
    var email = ""; // Email não é mais coletado
    var atendimento = data.atendimento;
    var recomendacao = data.recomendacao;
    var comentario = data.comentario || ""; // Comentário é opcional
    var recepcao = data.recepcao || "";
    
    // Adicionar o registro à planilha (Recepção é a primeira coluna)
    sheet.appendRow([recepcao, timestamp, email, atendimento, recomendacao, comentario]);
    
    // Retornar resposta de sucesso
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      data: data
    }))
    .setMimeType(ContentService.MimeType.JSON)
    .setHeader('Access-Control-Allow-Origin', '*')
    .setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    .setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
  } catch (error) {
    // Registrar o erro para depuração
    console.error("Erro ao processar submissão: " + error.toString());
    
    // Retornar resposta de erro
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      error: error.toString()
    }))
    .setMimeType(ContentService.MimeType.JSON)
    .setHeader('Access-Control-Allow-Origin', '*')
    .setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    .setHeader('Access-Control-Allow-Headers', 'Content-Type');
  } finally {
    // Liberar o bloqueio se existir
    const lock = LockService.getScriptLock();
    if (lock.hasLock()) {
      lock.releaseLock();
    }
  }
}

// Adicionar função doOptions para responder a preflight requests
function doOptions(e) {
  return ContentService.createTextOutput("")
    .setMimeType(ContentService.MimeType.TEXT)
    .setHeader('Access-Control-Allow-Origin', '*')
    .setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    .setHeader('Access-Control-Allow-Headers', 'Content-Type')
    .setHeader('Access-Control-Max-Age', '3600');
}

// Função para testar a configuração
function testSetup() {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Sheet1");
    
    if (!sheet) {
      return "Erro: Aba 'Sheet1' não encontrada. Execute a função initialSetup primeiro.";
    }
    
    // Verificar se os cabeçalhos estão corretos
    var headers = sheet.getRange("A1:F1").getValues()[0];
    var expectedHeaders = ["Recepção", "Timestamp", "Email", "Atendimento", "Recomendação", "Comentário"];
    
    for (var i = 0; i < expectedHeaders.length; i++) {
      if (headers[i] !== expectedHeaders[i]) {
        return "Erro: Cabeçalhos não configurados corretamente. Execute a função initialSetup.";
      }
    }
    
    // Verificar permissões de URL
    var scriptProperties = PropertiesService.getScriptProperties();
    var deploymentId = scriptProperties.getProperty("deploymentId");
    
    if (!deploymentId) {
      return "Aviso: Script ainda não implantado como Web App. Implante o script seguindo as instruções do README.";
    }
    
    return "Configuração testada com sucesso! O sistema está pronto para receber avaliações.";
  } catch (error) {
    return "Erro ao testar configuração: " + error.toString();
  }
} 