// Custom script to further process the output of main.py according to the author's specific needs
// Basically filter some things out, categorize the rest, and print the results for copy-pasting into a spreadsheet
// If you're reading this and you are not the author, you can ignore this file
//
// Every skipped transaction is logged to stderr (the task log); the stdout
// lines are the import text, with the Notes column marking the source.

const fs = require('fs')

const IMPORT_NOTE = 'Imported from Wealthsimple'

const transactions = JSON.parse(fs.readFileSync(process.argv[2]).toString())

const desiredTransactionDataByType = {
    'dividend reinvested': { finalType: 'Investment Buy' },
    'dividend': { finalType: 'Dividend' },
    'recurring buy': { finalType: 'Investment Buy' },
    'fractional buy': { finalType: 'Investment Buy' },
    'fractional sell': { finalType: 'Investment Sell' },
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
const positiveFinalTypes = ['Investment Sell', 'Dividend', 'Interest']

// Amounts arrive as pure currency values ("$54.50 CAD", "US$1,234.56").
// Strip the currency decorations, and mark an unlabelled US$ amount as USD.
// The absolute value is used because the final type decides the sign (the
// scraper may render negatives with either a Unicode or ASCII minus).
const parseAmount = (value) => parseFloat(String(value).replace(/[^0-9.-]/g, ''))
const currencyOf = (value) => {
    const code = /([A-Z]{3})\s*$/.exec(String(value))
    return code ? code[1] : (/US\$/.test(String(value)) ? 'USD' : 'CAD')
}
const describe = (transaction) =>
    `${transaction.date.slice(0, 10)} | ${transaction.description} | ${transaction.type} | ${transaction.amount}`

const filteredParsedTransactions = []
const skipped = { unsupported: 0, description: 0, ignored: 0, amount: 0 }

const additionalIgnoreFilters = {
    'Investment Buy': new Set(['CASH', 'MNY']),
    'Investment Sell': new Set(['CASH', 'MNY'])
}

for (let i = 0; i < transactions.length; i++) {
    const desiredTypeData = desiredTransactionDataByType[transactions[i].type.toLowerCase()] || desiredTransactionDataByDescription[transactions[i].description.toLowerCase()]
    const swapDescriptionAndType = !!desiredTransactionDataByDescription[transactions[i].description.toLowerCase()]
    if (!desiredTypeData) {
        skipped.unsupported += 1
        console.error(`Skipped (unsupported type): ${describe(transactions[i])}`)
        continue
    }
    if (desiredTypeData.alsoMatchDescription && desiredTypeData.alsoMatchDescription != transactions[i].description) {
        skipped.description += 1
        console.error(`Skipped (description mismatch): ${describe(transactions[i])}`)
        continue
    }
    if (!!additionalIgnoreFilters[desiredTypeData.finalType] && additionalIgnoreFilters[desiredTypeData.finalType].has(transactions[i].description)) {
        skipped.ignored += 1
        console.error(`Skipped (${desiredTypeData.finalType} ${transactions[i].description}): ${describe(transactions[i])}`)
        continue
    }
    const amount = Math.abs(parseAmount(transactions[i].amount))
    if (!Number.isFinite(amount)) {
        skipped.amount += 1
        console.error(`Skipped (unparseable amount): ${describe(transactions[i])}`)
        continue
    }
    filteredParsedTransactions.push({
        date: transactions[i].date.slice(0,10),
        description: !swapDescriptionAndType ? `${transactions[i].description} ${transactions[i].type}` : transactions[i].type,
        amount: amount * (positiveFinalTypes.indexOf(desiredTypeData.finalType) >= 0 ? 1 : -1),
        currency: currencyOf(transactions[i].amount),
        type: desiredTypeData.finalType || (!swapDescriptionAndType ? transactions[i].type : transactions[i].description)
    })
}

const skippedTotal = skipped.unsupported + skipped.description + skipped.ignored + skipped.amount
console.error(`Filtered ${transactions.length} scraped transactions -> ${filteredParsedTransactions.length} import lines (${skippedTotal} skipped: ${skipped.unsupported} unsupported type, ${skipped.ignored} CASH/MNY, ${skipped.description} description mismatch, ${skipped.amount} unparseable amount).`)

for (let i = filteredParsedTransactions.length - 1; i >= 0; i--) {
    console.log(`${filteredParsedTransactions[i].date}\t${filteredParsedTransactions[i].description}${filteredParsedTransactions[i].amount < 0 ? '\t\t' : '\t'}${Math.abs(filteredParsedTransactions[i].amount)}${filteredParsedTransactions[i].amount < 0 ? '\t' : '\t\t'}${filteredParsedTransactions[i].currency}\t${filteredParsedTransactions[i].type}\t${IMPORT_NOTE}`)
}
