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
        compareDigest
      }
    }
  }
}
'''
# TODO since we are using compareDigest to guarantee integrity, and to keep data clean, 
# I should not allow 2 entries for the same sku in 'actualizar cantidades'

get_variants_from_products_query=\
'''
query GetVariantsFromProductsQuery {
  products(first: 50, query:"%s") {
    nodes {
      vendor
      title
      metafields (first:2, keys:["custom.estado","custom.pueblo"]) {
        nodes {
          key
          value
        }
      }
      variants (first: 5) {
        nodes {
          title
          price
          sku
          inventoryItem {
            id
            unitCost {
              amount
            }
            inventoryLevel(locationId: "gid://shopify/Location/101430165822") {
              quantities (names: ["available"]) {
                quantity
              }
            }
          }
          metafield (namespace: "custom", key: "cost_history") {
            jsonValue
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
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

set_metafields=\
'''
mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields {
      namespace
      key
      value
      compareDigest
    }
    userErrors {
      field
      message
      code
    }
  }
}
'''
