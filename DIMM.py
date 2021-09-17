		#self.Prev_bAsk = None # previous best ask
        #self.Prev_bBid = None # previous best bid
        #self.Cur_bAsk = None # current best ask
        #self.Cur_bBid = None # current best bid

        #self.GAsk_min = bse_sys_maxprice # global ask minima
        #self.LAsk_min = bse_sys_maxprice # local ask minima
		#self.GBid_max = bse_sys_minprice # global bid maxima
        #self.LBid_max = bse_sys_minprice # local bid maxima


#self.ttype = ttype  # what type / strategy this trader is
#self.tid = tid  # trader unique ID code
#self.balance = balance  # money in the bank
#self.blotter = []  # record of trades executed
#self.orders = []  # customer orders currently being worked (fixed at 1)
#self.n_quotes = 0  # number of quotes live on LOB
#self.birthtime = time  # used when calculating age of a trader/strategy
#self.profitpertime = 0  # profit per unit time
#self.n_trades = 0  # how many trades has this trader done?
#self.lastquote = None  # record of what its last quote was
bse_sys_minprice = 1  # minimum price in the system, in cents/pennies
bse_sys_maxprice = 1000  # maximum price in the system, in cents/pennies

class Trader_DIMM01 (Trader):

    def __init__(self, ttype, tid, balance, time):
        Trader.__init__(self, ttype, tid, balance, time)

        self.job = 'Bid' #switches between 'Bid' and 'Ask'
        self.last_purchase_price = None # null before first trade
        self.bid_delta = 1 # how much (absolut value) to improve on best ask when buying
        self.ask_delta = 5 # how much (absolut value) to improve on purchase price
        self.active = False 
        #self.price = None
        self.roster_limit= 3
        self.roster_space= 3
        self.roster = []
        self.buy_limit = self.balance/self.roster_space
        self.sell_limit=None
        self.worth_Buy = False
        self.worth_Sell = False
        self.can_Buy = True
        self.can_Sell = False
        #self.n_trades = 0  # how many trades has this trader done?

        # memory of best price & quantity of best bid and ask, on LOB on previous update
        self.prev_best_bid_p = None
        self.prev_best_bid_q = None
        self.prev_best_ask_p = None
        self.prev_best_ask_q = None

        self.bid_improved = False
        self.bid_hit = False
        self.ask_improved = False
        self.ask_lifted = False

        # Used to dodge early expensive buys when only Shavers & Snipers are present in market
        self.anti_Shave = False 

        self.Local_Ask_minima = bse_sys_maxprice # local ask minima
        self.minSwitch = False
        self.minCount = 0
        self.Local_Bid_maxima = bse_sys_minprice # local bid maxima
        self.maxSwitch = False

        self.dist_AB = None
        self.alpha_rate = None


    #copy of GVWY's getorder
    def getorder(self, time, countdown, lob):
        if len(self.orders) < 1:
            order = None
            print('empty order')
        else:
            print('1 order')
            self.active = True 
            quoteprice = self.orders[0].price
            order = Order(self.tid,
                          self.orders[0].otype,
                          quoteprice,
                          self.orders[0].qty,
                          time, lob['QID'])
            self.lastquote = order
        return order

    def del_order(self, order):
        # this is lazy: assumes each trader has only one customer order with quantity=1, so deleting sole order
        # CHANGE TO DELETE THE HEAD OF THE LIST AND KEEP THE TAIL
        self.orders = []
        self.n_quotes = 0

    def bookkeep(self, trade, order, verbose, time):

        outstr = ""
        for order in self.orders:
            outstr = outstr + str(order)

        self.blotter.append(trade) #add trade record to trader's blotter
        # NB what follows is LAZY -- it assumes all orders are qty=1
        transactionprice = trade['price']

        bidTrans = True #did I buy? (for output logging only)
        if self.orders[0].otype == 'Bid':
            # Bid order succeeded, remember the price and adjust the balance
            self.balance -= transactionprice
            self.last_purchase_price = transactionprice
            self.job = 'Sell' # not try to sell it for a profit
        elif self.orders[0].otype == 'Ask':
            bidTrans = False # we made a sale (for output logging only)
            # Sold! put the money in the bank
            self.balance += transactionprice
            self.last_purchase_price = 0
            self.job = 'Buy' # now go back and buy another one
        else:
            sys.exit('FATAL: DIMM01 doesn\'t know .otype %s\n' % self.orders[0].otype)

        self.n_trades += 1

        verbose = False # We will log to output

        if verbose: # The following is for logging output to terminal
            if bidTrans: # We bought some shares
                outcome = "Bght"
                owned = 1
            else:
                outcome = "Sold"
                owned = 0
            net_worth = self.balance + self.last_purchase_price
            print('%s, %s=%d;  Qty=%d;  Balance=%d,  NetWorth=%d' %
                (outstr, outcome, transactionprice, owned, self.balance, net_worth))
            print()
        self.del_order(order) # delete the order







    def respond(self, time, lob, trade, verbose):
        
        def postBuyOrder():
            price = lob['asks']['best']
            self.orders.append( Order(self.tid, 'Bid', price, 1, time, lob['QID']) )

        self.mutate(time, lob, trade, True)
        
        if(self.job == 'Bid' and self.worth_Buy): #and not self.active ):
            postBuyOrder()


        self.prev_best_bid_p = lob['bids']['best']
        self.prev_best_ask_p = lob['asks']['best']


    def mutate(self, time, lob, trade, verbose):
        
        def lob_status(lob, trade, verbose):
            # what, if anything, has happened on the bid LOB?
            bid_improved = False
            bid_hit = False
            lob_best_bid_p = lob['bids']['best']
            lob_best_bid_q = None
            if lob_best_bid_p is not None:
                # non-empty bid LOB
                lob_best_bid_q = lob['bids']['lob'][-1][1]
                if (self.prev_best_bid_p is not None) and (self.prev_best_bid_p < lob_best_bid_p):
                    # best bid has improved
                    # NB doesn't check if the improvement was by self
                    bid_improved = True
                elif trade is not None and ((self.prev_best_bid_p > lob_best_bid_p) or (
                        (self.prev_best_bid_p == lob_best_bid_p) and (self.prev_best_bid_q > lob_best_bid_q))):
                    # previous best bid was hit
                    bid_hit = True
            elif self.prev_best_bid_p is not None:
                # the bid LOB has been emptied: was it cancelled or hit?
                last_tape_item = lob['tape'][-1]
                if last_tape_item['type'] == 'Cancel':
                    bid_hit = False
                else:
                    bid_hit = True

            # what, if anything, has happened on the ask LOB?
            ask_improved = False
            ask_lifted = False
            lob_best_ask_p = lob['asks']['best']
            lob_best_ask_q = None
            if lob_best_ask_p is not None:
                # non-empty ask LOB
                lob_best_ask_q = lob['asks']['lob'][0][1]
                if (self.prev_best_ask_p is not None) and (self.prev_best_ask_p > lob_best_ask_p):
                    # best ask has improved -- NB doesn't check if the improvement was by self
                    ask_improved = True
                elif trade is not None and ((self.prev_best_ask_p < lob_best_ask_p) or (
                        (self.prev_best_ask_p == lob_best_ask_p) and (self.prev_best_ask_q > lob_best_ask_q))):
                    # trade happened and best ask price has got worse, or stayed same but quantity reduced
                    # -- assume previous best ask was lifted
                    ask_lifted = True
            elif self.prev_best_ask_p is not None:
                # the ask LOB is empty now but was not previously: canceled or lifted?
                last_tape_item = lob['tape'][-1]
                if last_tape_item['type'] == 'Cancel':
                    ask_lifted = False
                else:
                    ask_lifted = True

            if verbose and (bid_improved or bid_hit or ask_improved or ask_lifted):
                print('B_improved-', bid_improved, '\tB_hit-', bid_hit, '\tA_improved-', ask_improved, '\tA_lifted-', ask_lifted)
            
            self.prev_best_bid_q = lob_best_bid_q
            self.prev_best_ask_q = lob_best_ask_q

            self.ask_improved = ask_improved
            self.ask_lifted = ask_lifted
            self.bid_improved = bid_improved
            self.bid_hit = bid_hit

        def update(lob):
            self.prev_best_bid_p = lob['bids']['best']
            self.prev_best_ask_p = lob['asks']['best']

        def isWorth_Buy(time):
            best_ask = lob['asks']['best']
            best_bid = lob['bids']['best']
            #finding the local minima of the ask prices just before it starts to rise again
            if self.minSwitch and (best_ask > self.prev_best_ask_p) and (not self.ask_lifted):
                #self.anti_Shaver = True
                self.minSwitch = False
                self.dist_AB = best_ask - best_bid

                if (best_ask > self.buy_limit):
                    self.worth_Buy = False
                elif ((best_ask/self.Local_Ask_minima) > 1.3) and (self.minCount < 5):
                    self.worth_Buy = False
                    self.minCount += 1
                #elif((self.dist_AB/best_bid) > 1.4):
                #    worth_Buy = False
                else:
                    self.worth_Buy = True
                    self.minCount = 0
                    #print('worth_Buy : (t ',round(time,2),')  \task ',best_ask,' bid ',best_bid,'\tLA_min ',self.Local_Ask_minima)
                    if (self.Local_Ask_minima > best_ask):
                        self.Local_Ask_minima = best_ask
                    #if(worth_Buy):
                    
            if(self.ask_improved): 
                self.minSwitch = True

        #def postOrder():

        if (lob['asks']['best'] is not None) and (lob['bids']['best'] is not None) and (self.prev_best_ask_p is not None):
            isWorth_Buy(time)

         
        lob_status(lob, trade, False)
        
        
        #print('%s : (t=%s) :  %s  <>  %s' %( self.tid,time, lob['bids']['best'], lob['asks']['best']))
        #print('DIMM is ready to trade ? - %s \n' %self.anti_Shaver)

