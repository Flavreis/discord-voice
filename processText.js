const inputText = process.argv[2];

processText(inputText).then(outputText => {
    console.log(outputText);
}).catch(error => {
    console.error('Erro ao processar o texto:', error);
    process.exit(1);
});
