# %%
#Analyse Products 
#
# Initialisation: 
# Read CSV file that maps a product to its component products (1 line per component), and define
# what quantity of each component is required for that product (units - as per the component).  
#
# createData - opens the hardcoded CSV file that is expected to contain rows containing these fields:
#
#           Item No.                  string identifying the product
#           No.                       string identifying a component product for Item No.
#           Quantity per              float (after cleaning) identifying units of No. to form Item No.
#           Item Replenishment System "Purchase" || "Prod. Order"
#           Current Unit Cost (LCY)   Current Unit Cost of of Item No. (NOT the )
#
# Create a dictionary of Items for each product which contains data including a List of 
# ComponentItem (Component Id & QtyPer)
#
#  NOTE: the BOM Unit Cost field that may be present defines the unit cost of a Component No. is not used.
#
# calculateProductTreeDepths - output the depth of the product tree for each product.  
# Warnings logged: where a product refers to a component product that is not defined as a product
# in the source data, this is logged in a the log attribute of the associated Item element .
#
# calculateProductRolledUpCosts - crawl the tree of components for each product in the Dictionary
# and calculate the qtyPerTop (multiple of the component product )
# 
# REVISION HISTORY
#

import pandas as pd     

# Globals used in the recusive function calculateProductTreeDepth to track the product level
currentLevel = 0
maxLevel = 0

# Flags to raise an error if recursive functions are called without first calling the 
# associated initialising function
calculateProductRolledUpCostSentinel = False
calculateProductTreeDepthSentinel = False

# Dictionary to hold catalogue of product data
# A dictionary key in python is any immutable data type eg int, float, string
# Key - product number - here, the product number is stored as a string so any
#                        lookup must use a string for the lookup to be successful
# Item - an object of class Item which contains information about the Product
itemsDictionary = {}      #instantiate the global dictionary

##############################################################################################
#  Data Definitions
#
class Item:
  # a class to represent an Item, including a list of component items
  def __init__(self, item_number, itemReplenishmentSystem, BOMUnitCost):
    self.item_number = item_number  # Item id
    self.level = -1                 #
    self.itemList = []              # List of ComponentItem objects
    self.log = []                   # List of log entries created as item is processed
    self.replenishmentSystem = itemReplenishmentSystem  # String read from data
    self.BOMUnitCost = BOMUnitCost
    # qtyPerTopITem - should be set to 1.0 for the top level product when creating rolled up cost
    # for that product
    self.qtyPerTopItem = 1.0    #Initialise this to 1.0 

  def clearLog(self):
    self.log.clear()


class ComponentItem:
  # Class ComponentItem - represents an the item and qtyPer that forms a component of a Product
  # store the Qty Per Parent against each component product in a Product's component tree
  # as this qty is different for different parent products  
  # If the input data is complete, a ComponentItem will have an Item object in the dictionary 
  # of products.  
  def __init__(self, itemNumber, qtyPer):
    self.itemNumber = itemNumber
    self.qtyPer = qtyPer


##################################################################################################
def remove_last_decimal_place(text):
    if text[-1] == '.':
        return text[:-1]
    else:
        return text

################################################################################################
def printItemAndComponents():
  # Print the item and list of component items
  for x in itemsDictionary:
    print (x)
    for y in itemsDictionary[x].itemList:
      print (f"   Component: {y.itemNumber}   Qty Per: {y.qtyPer}")



##################################################################################################
# Function to iterate over the rows in a Panda Data Frame in  which each row maps a Product to a 
# component Product - a one to many relationship, so can be more than one row for a product.
# For each row, an item is created and added to the global dictionary of Items
##################################################################################################
def createData():

  # Read data from file
  df = pd.read_csv('rll-items-bom-with-cost.csv')

  # Clean up data - RLT
  df['Quantity per'] = df.apply(lambda x: x['Quantity per'].replace(',', ''), axis=1)
  df['Quantity per'] = df.apply(lambda x: remove_last_decimal_place(x['Quantity per']), axis=1)
  df["Quantity per"] = pd.to_numeric(df["Quantity per"])
  df['Quantity per'].head()

  for index, row in df.iterrows():
    # print(row['Item No.'], row['No.'])
    
    itemNumber = row['Item No.']
    itemComponent = row['No.']
    itemComponentQtyPer = row['Quantity per'] 
    itemReplenishmentSystem = row['Item Replenishment System']
    itemBOMUnitCost = row['Current Unit Cost (LCY)']
    
    invalidItemValueDetected = False

    if pd.isna(itemNumber) == False: 
      # Try to convert - some of the itemNumbers are not numbers  
      try:
        # itemNumber = str(itemNumber)   
        itemNumber = int(itemNumber)
      except ValueError:
        invalidItemValueDetected = True
        itemNumber - "NAN"
    else:
      itemNumber = "NAN"
      invalidItemValueDetected = True

    # Store the itemNumber as a string to use as the index in the dictionary
    # As we have chosen for the Key in the dictionary to be a string so any lookup must use type string.
    itemNumber=str(itemNumber)
      
    if pd.isna(itemComponent) == False:
      itemComponent = int(itemComponent)   # Force the component number to integer rather than float
      itemComponent = str(itemComponent)   # Force the integer version of product id to a string to store in list
      
    if itemNumber in itemsDictionary:
      # Item already in dictionary - there can be more than one row for a item, 1 for each component item
      pass #Do nothing
    else:
      # Create Item object for this product and add to the dictionary
      itemObject = Item(itemNumber, itemReplenishmentSystem, itemBOMUnitCost)     
      itemsDictionary.update({itemNumber: itemObject})

    # Get a reference to the Item object for the product
    itemReference = itemsDictionary[itemNumber]
    
    if pd.isna(itemComponent) == False:
      if itemComponent in itemReference.itemList:    
        #Python f string used as shorthand to change variables to strings for output.
        itemReference.log.append(f"Product {itemNumber} refers to component product {itemComponent} more than once.")
      
      component = ComponentItem(itemComponent, itemComponentQtyPer)
      itemReference.itemList.append(component)

      component = itemReference.itemList[-1]  # Get reference to the item added to the list...
      # print (f"Adding component for {itemNumber} Component - {component.itemNumber}, QtyPer - {component.qtyPer}")

    else:
      # itemComponent is not a number - eg when item has no component item
      pass

    if invalidItemValueDetected == True:
      itemReference.log.append(f"Non-numeric Item No. detected in raw data, value read was: {itemNumber} on row {index}")


############################################################################################################
# reportProductWarnings
def reportProductWarnings():
  print("================================== ")
  print("=== Warnings About Source Data === ")
  print("================================== ")
  for x in itemsDictionary:
    for logItem in itemsDictionary[x].log:
      print ("     ",logItem)

############################################################################################################
# resetProductWarnings
def resetProductWarnings():
  # Empty the log for each item in the Product dictionary
  for x in itemsDictionary:
    itemsDictionary[x].clearLog()

############################################################################################################
# validateProductTree
# Look for Products in the dictionary which have component products that are not in the dictionary.
def validateProductTree():

  # Iterate over all the products in the catalogue to discover and record max product depth for each
  for x in itemsDictionary:  
    itemReference = itemsDictionary[str(x)]

    for itemComponent in itemReference.itemList:
      if str(itemComponent.itemNumber) in itemsDictionary:
        # The item is in the dictionary - nothing to report
        pass
      
      else:
        # Could not find item in the Dictionary - a product referenced by a product
        # was not defined in the input data
        itemReference.log.append(f"Product {itemReference.item_number} refers to product {itemComponent.itemNumber} for which there is no definition in the source data.")


############################################################################################################
# calculateProductTreeDepths
def calculateProductTreeDepths():

  # Make explicit we are referring to global variables not function locals
  global itemsDictionary
  global currentLevel 
  global maxLevel
  global calculateProductTreeDepthSentinel

  calculateProductTreeDepthSentinel = True  # Flag used to check that this function is called
                                            # to start the crawl, rather than the recusive function
 
  # Iterate over all the products in the catalogue to discover and record max product depth for each
  for x in itemsDictionary:  
    currentLevel = 0   # Reset global
    maxLevel = 0 # Reset global
    calculateProductTreeDepth(str(x))

    # Record the product tree depth for the item
    itemsDictionary[x].level = maxLevel

  calculateProductTreeDepthSentinel = False
  


############################################################################################################
# calculateProductTreeDepth
# Function to crawl through the component products referenced by product with id itemName.
# RECURSIVE Function that is should be called initially by calculateProductTreeDepths
# which encapsulates the prerequisites of invoking this function.
# 
# Uses the globals currentLevel and maxLevel to track the depth of the product tree - before
# the first call to calculateProductTreeDepth these should be set to 0 to allow the recursion to leave maxLevel on return to 
# contain the depth of the tree.
def calculateProductTreeDepth(itemName):

   # Make explicit we are referring to global variables not function locals
  global itemsDictionary
  global currentLevel 
  global maxLevel
  global calculateProductTreeDepthSentinel

  if calculateProductTreeDepthSentinel == False:
    raise Exception("calculateProductTreeDepth called without calling initialising function calculateProductTreeDepths")
  else:
   
   itemReference = itemsDictionary[itemName]

   for x in itemsDictionary[itemName].itemList:

      # Increment the currentLevel in the tree of product items
      currentLevel = currentLevel + 1

      # Check if the component item is in the itemsDictionary - force the list item to string.
      if str(x.itemNumber) in itemsDictionary:
         calculateProductTreeDepth(str(x.itemNumber))

      else:
         # Could not find item in the Dictionary - a product referenced by a product
         # was not defined in the input data
         itemReference.log.append(f"Product {itemName} refers to product {x.itemNumber} for which there is no definition in the source data.")

      # Update the global maxLevel so that the recursive crawl through the top level product remembers
      # the deepest level.
      if maxLevel < currentLevel:
         maxLevel = currentLevel

      # Decerement currentLevel as we unwind the recursion
      currentLevel = currentLevel - 1


############################################################################################################
# calculateProductRolledUpCosts
#
# Function to crawl through all products in the Product dictionary to calculate their rolled
# up product cost
############################################################################################################
def calculateProductRolledUpCosts(conciseOutput):

  global totalComponentCost
  global calculateProductRolledUpCostSentinel

  calculateProductRolledUpCostSentinel=True

  for x in itemsDictionary:

   itemReference = itemsDictionary[x]  

   # Flag to to control detail of output
   conciseOutput = False

   # To create rolled up cost for this product, set total component cost to 0 before starting
   # to crawl the tree
   totalComponentCost = 0.0
   itemReference.qtyPerTopItem = 1.0 # For the top item in a tree, this must be 1.0

   if conciseOutput == False:
      print (f"Product: {x}")
      calculateProductRolledUpCost(x,1,True)  # silent = true to suppress output as crawl the tree
   
      for logItem in itemReference.log:
        print ("     ",logItem)

      print (f"   TOTAL COMPONENT COST: {round(totalComponentCost,4)}")
      print("")

   else:
      # Concise Output - Product Number, Rolled Up Cost and Warnings
      calculateProductRolledUpCost(x,1,False)  # silent = false to output component data as crawl the tree
      print (f"Product {x} Rolled Up Cost: {round(totalComponentCost,4)}")
      for logItem in itemReference.log:
         print ("     ",logItem)

  calculateProductRolledUpCostSentinel=False
      

############################################################################################################
# calculateProductRolledUpCost
#
# Function to crawl through the component products referenced by product with id itemName and to output
# a description of the component items.
############################################################################################################
def calculateProductRolledUpCost(itemNumber, level, silent):

  global calculateProductRolledUpCostSentinel

  if calculateProductRolledUpCostSentinel == False:
    raise Exception("calculateProductRolledUpCost called without calling initialising function calculateProductRolledUpCosts")
  else:
    # Whilst navigating the tree of components, add the BOM cost of any component product which is 
    # categorised as ReplenishmentSystem = "Purchase" to the global componentCost
    global totalComponentCost 

    itemReference = itemsDictionary[itemNumber]
    parentQtyPerTopItem = itemReference.qtyPerTopItem
    
    componentCost = 0.0
    itemReplenishmentSystem = "Unknown"

    for x in itemReference.itemList: 
        # Iterate over all the ComponentItem objects in the itemList for itemNumber
        if str(x.itemNumber) in itemsDictionary:
          itemChild = itemsDictionary[x.itemNumber]
          itemReplenishmentSystem = itemChild.replenishmentSystem

          #  Set up the Quantity per Top Item 
          itemChild.qtyPerTopItem = parentQtyPerTopItem * x.qtyPer
        
          # Only add in the cost of items that are of replenishment type Purchase
          if itemReplenishmentSystem == "Purchase":
              componentCost = float(itemChild.BOMUnitCost) * itemChild.qtyPerTopItem
              totalComponentCost = totalComponentCost + componentCost

          strIndent = ""
          for a in range(1,level+1):
            strIndent = strIndent+"\t"

          if silent == False:
              print(strIndent + \
                    f"{x.itemNumber}\tQtyPer:{round(x.qtyPer,2)}\tCompCost:{round(componentCost,2)}\tQtyPerTop:{round(itemChild.qtyPerTopItem,2)}")
              print(strIndent + f"Replen:{itemReplenishmentSystem}\tUnitCost:{itemChild.BOMUnitCost}")

          calculateProductRolledUpCost(str(x.itemNumber),level+1, silent)

        else:
          # Could not find item in the Dictionary   - a product referenced by a product
          # was not defined in the input data
          itemReference.log.append(f"Product {itemNumber} refers to product {x.itemNumber} for which there is no definition in the source data.")



 
if __name__ == "__main__":
  # Run this code if the module is run directly
  
  # Populate itemsDictionary catalogue of products from Pandas DF
  createData()

  # REPORTING
  # 1. Output any warnings after the input data is validated - eg Component Products for 
  # which there is no full Product definition.  This type of error may make the 
  # product level or rolled up costs incorrect.
  resetProductWarnings()
  validateProductTree()
  reportProductWarnings()

  # 2. Output the product level for each product
  resetProductWarnings()
  calculateProductTreeDepths()
  #  Report the item level for each product
  print("")
  print("================================== ")
  print("=== Product Levels per Product === ")
  print("================================== ")
  for x in itemsDictionary:
      print ("Item "+ str(itemsDictionary[x].item_number) + " Level - " + str(itemsDictionary[x].level))
  ### reportProductWarnings()


  # 3. Output Verbose or Concise Report Of Rolled Up Cost Each Product
  resetProductWarnings()
  # Report the rolled up costs per product

  conciseRolledUpCostReport = True
  
  print("")
  print("============================================================================== ")
  print(f"=== Product Rolled Up Costs   Concise Report? {conciseRolledUpCostReport}                      === ")
  print("============================================================================== ")
 
  # calculateProductRolledUpCosts(conciseRolledUpCostReport)    # False means verbose output
  calculateProductRolledUpCosts(conciseRolledUpCostReport)   # True means concise report - just rolled up costs
  ###reportProductWarnings()

  # DEBUG TOOL printItemsAndComponents()




