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
  }
}
'''

adjust_variant_quantities=\
'''
mutation adjustVariantsQuantities($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    userErrors {
      field
    }
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
  }
}
'''