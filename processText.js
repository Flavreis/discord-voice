import { pipeline } from '@xenova/transformers';

async function processText(inputText) {
    const model = await pipeline('text2text-generation', 't5-small'); // Ou qualquer outro modelo adequado
    const output = await model(inputText);
    return output[0].generated_text;
}

const inputText = process.argv[2];

processText(inputText).then(outputText => {
    console.log(outputText);
}).catch(error => {
    console.error('Erro ao processar o texto:', error);
    process.exit(1);
});
