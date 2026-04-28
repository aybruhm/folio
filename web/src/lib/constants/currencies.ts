export interface CurrencyOption {
  value: string;
  label: string;
}

export const CURRENCIES: CurrencyOption[] = [
  // Americas
  { value: 'USD', label: 'USD - US Dollar' },
  { value: 'CAD', label: 'CAD - Canadian Dollar' },
  { value: 'BRL', label: 'BRL - Brazilian Real' },
  { value: 'MXN', label: 'MXN - Mexican Peso' },
  { value: 'ARS', label: 'ARS - Argentine Peso' },
  { value: 'CLP', label: 'CLP - Chilean Peso' },
  { value: 'COP', label: 'COP - Colombian Peso' },
  { value: 'PEN', label: 'PEN - Peruvian Sol' },

  // Europe
  { value: 'EUR', label: 'EUR - Euro' },
  { value: 'GBP', label: 'GBP - British Pound' },
  { value: 'CHF', label: 'CHF - Swiss Franc' },
  { value: 'SEK', label: 'SEK - Swedish Krona' },
  { value: 'NOK', label: 'NOK - Norwegian Krone' },
  { value: 'DKK', label: 'DKK - Danish Krone' },
  { value: 'PLN', label: 'PLN - Polish Zloty' },
  { value: 'CZK', label: 'CZK - Czech Koruna' },
  { value: 'HUF', label: 'HUF - Hungarian Forint' },
  { value: 'RON', label: 'RON - Romanian Leu' },
  { value: 'TRY', label: 'TRY - Turkish Lira' },
  { value: 'RUB', label: 'RUB - Russian Ruble' },

  // Middle East & Africa
  { value: 'ILS', label: 'ILS - Israeli Shekel' },
  { value: 'AED', label: 'AED - UAE Dirham' },
  { value: 'SAR', label: 'SAR - Saudi Riyal' },
  { value: 'QAR', label: 'QAR - Qatari Riyal' },
  { value: 'KWD', label: 'KWD - Kuwaiti Dinar' },
  { value: 'EGP', label: 'EGP - Egyptian Pound' },
  { value: 'NGN', label: 'NGN - Nigerian Naira' },
  { value: 'ZAR', label: 'ZAR - South African Rand' },
  { value: 'KES', label: 'KES - Kenyan Shilling' },
  { value: 'GHS', label: 'GHS - Ghanaian Cedi' },
  { value: 'MAD', label: 'MAD - Moroccan Dirham' },

  // Asia Pacific
  { value: 'JPY', label: 'JPY - Japanese Yen' },
  { value: 'CNY', label: 'CNY - Chinese Yuan' },
  { value: 'HKD', label: 'HKD - Hong Kong Dollar' },
  { value: 'KRW', label: 'KRW - South Korean Won' },
  { value: 'TWD', label: 'TWD - Taiwanese Dollar' },
  { value: 'SGD', label: 'SGD - Singapore Dollar' },
  { value: 'INR', label: 'INR - Indian Rupee' },
  { value: 'AUD', label: 'AUD - Australian Dollar' },
  { value: 'NZD', label: 'NZD - New Zealand Dollar' },
  { value: 'MYR', label: 'MYR - Malaysian Ringgit' },
  { value: 'THB', label: 'THB - Thai Baht' },
  { value: 'IDR', label: 'IDR - Indonesian Rupiah' },
  { value: 'PHP', label: 'PHP - Philippine Peso' },
  { value: 'VND', label: 'VND - Vietnamese Dong' },
  { value: 'PKR', label: 'PKR - Pakistani Rupee' },
  { value: 'BDT', label: 'BDT - Bangladeshi Taka' },
  { value: 'LKR', label: 'LKR - Sri Lankan Rupee' },
];

export const CURRENCY_VALUES = CURRENCIES.map((c) => c.value) as [string, ...string[]];
