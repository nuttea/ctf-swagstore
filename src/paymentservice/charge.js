// Copyright 2018 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
const tracer = require('dd-trace').init();
const cardValidator = require('simple-card-validator');
const { v4: uuidv4 } = require('uuid');
const pino = require('pino');
const formats = require('dd-trace/ext/formats');

const logger = pino({
  name: 'paymentservice-charge',
  messageKey: 'message',
  formatters: {
    level (logLevelString, logLevelNum) {
      return { severity: logLevelString }
    },
    log(obj) {
          // ログの前にタイムスタンプを追加
          obj.timestamp = new Date().toISOString();  // ISO形式のタイムスタンプ
          return obj;
    }
  }
});


class CreditCardError extends Error {
  constructor (message) {
    super(message);
    this.code = 400; // Invalid argument error
  }
}

class InvalidCreditCard extends CreditCardError {
  constructor (cardType) {
    super(`Credit card info is invalid`);
  }
}

class UnacceptedCreditCard extends CreditCardError {
  constructor (cardType) {
    super(`Sorry, we cannot process ${cardType} credit cards. Only VISA or MasterCard is accepted.`);
  }
}

class ExpiredCreditCard extends CreditCardError {
  constructor (number, month, year) {
    super(`Your credit card (ending ${number.substr(-4)}) expired on ${month}/${year}`);
  }
}
class SpecificYearCreditCardError extends CreditCardError {
  constructor(year) {
    super(`Credit cards with an expiration year of ${year} are not accepted. The flag is "bits"`);
  }
}

/**
 * Verifies the credit card number and (pretend) charges the card.
 *
 * @param {*} request
 * @return transaction_id - a random uuid.
 */
module.exports = function charge (request) {
  const { amount, credit_card: creditCard } = request;
  const cardNumber = creditCard.credit_card_number;
  const cardInfo = cardValidator(cardNumber);
  const {
    card_type: cardType,
    valid
  } = cardInfo.getCardDetails();
  const span = tracer.scope().active();
  const traceId = span ? span.context().toTraceId() : 'no-trace';
  const spanId = span ? span.context().toSpanId() : 'no-span';

  //console.log(`[Trace ID: ${traceId}, Span ID: ${spanId}] Card number: ${cardNumber}`); // デバッグ用ログ
  //console.log(`Card type: ${cardType}`); // デバッグ用ログ
  //console.log(`Card valid: ${valid}`); // デバッグ用ログ
  //console.log(`Expiration year: ${creditCard.credit_card_expiration_year}`); // デバッグ用ログ
  //console.log(`Expiration month: ${creditCard.credit_card_expiration_month}`); // デバッグ用ログ

  if (!valid) { throw new InvalidCreditCard(); }

  // Only VISA and mastercard is accepted, other card types (AMEX, dinersclub) will
  // throw UnacceptedCreditCard error.
  if (!(cardType === 'visa' || cardType === 'mastercard')) { throw new UnacceptedCreditCard(cardType); }

  // Also validate expiration is > today.
  const currentMonth = new Date().getMonth() + 1;
  const currentYear = new Date().getFullYear();
  const { credit_card_expiration_year: year, credit_card_expiration_month: month } = creditCard;
  // Specific check for the year 2025
  if (year === 2025) {
   logger.error(`SpecificYearCreditCardError: Credit cards with an expiration year of ${year} are not accepted. The flag is "bits" Trace ID: ${traceId}`);
   throw new SpecificYearCreditCardError(year); }
  if ((currentYear * 12 + currentMonth) > (year * 12 + month)) { throw new ExpiredCreditCard(cardNumber.replace('-', ''), month, year); }

  logger.info(`Transaction processed: ${cardType} ending ${cardNumber.substr(-4)} expiration year ${year} \
    Amount: ${amount.currency_code}${amount.units}.${amount.nanos} Trace ID: ${traceId}`);

  return { transaction_id: uuidv4() };
};
