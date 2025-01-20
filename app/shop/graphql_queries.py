TESTING_QUERY = \
'''
query Test {
  products(first: 3) {
    edges {
      node {
        id
        title
      }
    }
  }
}
'''

get_variants_by_sku=\
'''
{
  productVariants(first: 3, query: "sku:%s") {
    nodes {
      id
      product {
        id
        vendor
      }
      price
      displayName
      inventoryItem {
        id
        unitCost {
          amount
        }
      }
      metafield (namespace: "custom", key: "cost_history") {
        jsonValue
      }
    }
  }
}
'''

set_variant_cost=\
'''
mutation inventoryItemUpdate($id: ID!, $input: InventoryItemInput!) {
  inventoryItemUpdate(id: $id, input: $input) {
    inventoryItem {
      id
      unitCost {
        amount
      }
    }
    userErrors {
      message
      field
    }
  }
}
'''

set_variant_price=\
'''
mutation setVariantPrice($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    product {
      id
    }
    productVariants {
      id
      displayName
      price
    }
    userErrors {
      field
      message
    }
  }
}
'''

adjust_variant_quantities=\
'''
mutation adjustVariantsQuantities($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    inventoryAdjustmentGroup {
      createdAt
      reason
      changes {
        name
        delta
        item {
          sku
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
'''