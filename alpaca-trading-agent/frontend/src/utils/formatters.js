/** Format an amount to USD */
export const formatUSD = (amount) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount || 0);
};

/** Format an order ID to first 8 characters */
export const formatOrderId = (id) => {
  if (!id) return '';
  return id.substring(0, 8);
};

/** Copy text to clipboard */
export const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
};
