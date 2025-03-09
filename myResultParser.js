const fs = require('fs')

const transactions = JSON.parse(fs.readFileSync(process.argv[2]).toString())

const desiredTransactionDataByType = {
    'dividend reinvested': { finalType: 'Investment Buy' },
    'dividend': { finalType: 'Dividend' },
    'recurring buy': { finalType: 'Investment Buy' },
    'fractional buy': { finalType: 'Investment Buy' },
    'market sell': { finalType: 'Investment Sell' },
    'limit buy': { finalType: 'Investment Buy' },
    'limit sell': { finalType: 'Investment Sell' },
    'invested cash': { finalType: 'Investment Buy' },
    'sold asset': { finalType: 'Investment Sell' }
}
const desiredTransactionDataByDescription = {
    'earnings': { finalType: 'Other Money In' },
    'interest': { finalType: 'Interest' },
    'cashback': { finalType: 'Interest' }
}
const positiveFinalTypes = ['Investment Sell', 'Dividend']

const filteredParsedTransactions = []

const additionalIgnoreFilters = {
    'Investment Buy': new Set(['CASH']),
    'Investment Sell': new Set(['CASH'])
}

for (let i = 0; i < transactions.length; i++) {
    const desiredTypeData = desiredTransactionDataByType[transactions[i].type.toLowerCase()] || desiredTransactionDataByDescription[transactions[i].description.toLowerCase()]
    const swapDescriptionAndType = !!desiredTransactionDataByDescription[transactions[i].description.toLowerCase()]
    if (desiredTypeData) {
        if (desiredTypeData.alsoMatchDescription && desiredTypeData.alsoMatchDescription != transactions[i].description) {
            continue
        }
        if (!!additionalIgnoreFilters[desiredTypeData.finalType] && additionalIgnoreFilters[desiredTypeData.finalType].has(transactions[i].description)) {
            continue
        }
        filteredParsedTransactions.push({
            date: transactions[i].date.slice(0,10),
            description: !swapDescriptionAndType ? `${transactions[i].description} ${transactions[i].type}` : transactions[i].type,
            amount: parseFloat(transactions[i].amount.replace('$', '').split(',').join('')) * (positiveFinalTypes.indexOf(desiredTypeData.finalType) >= 0 ? 1 : -1),
            currency: RegExp(' [A-Z]+$').exec(transactions[i].amount)[0].trim(),
            type: desiredTypeData.finalType || (!swapDescriptionAndType ? transactions[i].type : transactions[i].description)
        })
    }
}

for (let i = filteredParsedTransactions.length - 1; i >= 0; i--) {
    console.log(`${filteredParsedTransactions[i].date}\t${filteredParsedTransactions[i].description}${filteredParsedTransactions[i].amount < 0 ? '\t\t' : '\t'}${Math.abs(filteredParsedTransactions[i].amount)}${filteredParsedTransactions[i].amount < 0 ? '\t' : '\t\t'}${filteredParsedTransactions[i].currency}\t${filteredParsedTransactions[i].type}`)
}