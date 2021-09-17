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
        else:
            
            self.active = True 
            quoteprice = self.orders[0].price
            order = Order(self.tid,
                          self.orders[0].otype,
                          quoteprice,
                          self.orders[0].qty,
                          time, lob['QID'])
            self.lastquote = order
        return order

    
    def bookkeep(self, trade, order, verbose, time):

        outstr = ""
        for order in self.orders:
            outstr = outstr + str(order)

        #print('Order len ',len(self.orders))
        self.blotter.append(trade) #add trade record to trader's blotter
        # NB what follows is LAZY -- it assumes all orders are qty=1
        transactionprice = trade['price']

        bidTrans = True #did I buy? (for output logging only)
        if self.orders[0].otype == 'Bid':
            # Bid order succeeded, remember the price and adjust the balance
            self.balance -= transactionprice
            self.last_purchase_price = transactionprice
            self.job = 'Ask' # not try to sell it for a profit
        

        elif self.orders[0].otype == 'Ask':
            bidTrans = False # we made a sale (for output logging only)
            # Sold! put the money in the bank
            self.balance += transactionprice
            self.last_purchase_price = 0
            self.job = 'Bid' # now go back and buy another one
        
        else:
            sys.exit('FATAL: DIMM01 doesn\'t know .otype %s\n' % self.orders[0].otype)


        if bidTrans: # We bought some shares
            outcome = "Bght"
            owned = 1
        else:
            outcome = "Sold"
            owned = 0


        self.n_trades += 1
        net_worth = self.balance + self.last_purchase_price
        verbose = True
        if verbose: # The following is for logging output to terminal
            if bidTrans: # We bought some shares
                outcome = "Bght"
                owned = 1
            else:
                outcome = "Sold"
                owned = 0
            net_worth = self.balance + self.last_purchase_price
            print('%s, %s=%d;  Qty=%d;  Balance=%d,  NetWorth=%d\n' %
                (outstr, outcome, transactionprice, owned, self.balance, net_worth))
        
        self.del_order(order) # delete the order
        self.active = False





    def respond(self, time, lob, trade, verbose):
        
        def postBuyOrder():
            price = lob['asks']['best']
            order = Order(self.tid, 'Bid', price, 1, time, lob['QID']) 
            self.orders= [order]


        def postSellOrder():
            price = self.last_purchase_price
            order = Order(self.tid, 'Ask', price, 1, time, lob['QID']) 
            self.orders= [order]


        def target_up(price):
            # generate a higher target price by randomly perturbing given price
            ptrb_abs = self.ca * random.random()  # absolute shift
            ptrb_rel = price * (1.0 + (self.cr * random.random()))  # relative shift
            target = int(round(ptrb_rel + ptrb_abs, 0))
            # #                        print('TargetUp: %d %d\n' % (price,target))
            return target

        def target_down(price):
            # generate a lower target price by randomly perturbing given price
            ptrb_abs = self.ca * random.random()  # absolute shift
            ptrb_rel = price * (1.0 - (self.cr * random.random()))  # relative shift
            target = int(round(ptrb_rel - ptrb_abs, 0))
            # #                        print('TargetDn: %d %d\n' % (price,target))
            return target

        def willing_to_trade(price):
            # am I willing to trade at this price?
            willing = False
            if self.job == 'Bid' and self.active and self.price >= price:
                willing = True
            if self.job == 'Ask' and self.active and self.price <= price:
                willing = True
            return willing

        def profit_alter(price):
            oldprice = self.price
            diff = price - oldprice
            change = ((1.0 - self.momntm) * (self.beta * diff)) + (self.momntm * self.prev_change)
            self.prev_change = change
            newmargin = ((self.price + change) / self.limit) - 1.0

            if self.job == 'Bid':
                if newmargin < 0.0:
                    self.margin_buy = newmargin
                    self.margin = newmargin
            else:
                if newmargin > 0.0:
                    self.margin_sell = newmargin
                    self.margin = newmargin

            # set the price from limit and profit-margin
            self.price = int(round(self.limit * (1.0 + self.margin), 0))

        # #                        print('old=%d diff=%d change=%d price = %d\n' % (oldprice, diff, change, self.price))

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
            print('B_improved', bid_improved, 'B_hit', bid_hit, 'A_improved', ask_improved, 'A_lifted', ask_lifted)

        deal = bid_hit or ask_lifted

        if self.job == 'Ask':
            # seller
            if deal:
                tradeprice = trade['price']
                if self.price <= tradeprice:
                    # could sell for more? raise margin
                    target_price = target_up(tradeprice)
                    profit_alter(target_price)
                elif ask_lifted and self.active and not willing_to_trade(tradeprice):
                    # wouldnt have got this deal, still working order, so reduce margin
                    target_price = target_down(tradeprice)
                    profit_alter(target_price)
            else:
                # no deal: aim for a target price higher than best bid
                if ask_improved and self.price > lob_best_ask_p:
                    if lob_best_bid_p is not None:
                        target_price = target_up(lob_best_bid_p)
                    else:
                        target_price = lob['asks']['worst']  # stub quote
                    profit_alter(target_price)

        if self.job == 'Bid':
            # buyer
            if deal:
                tradeprice = trade['price']
                if self.price >= tradeprice:
                    # could buy for less? raise margin (i.e. cut the price)
                    target_price = target_down(tradeprice)
                    profit_alter(target_price)
                elif bid_hit and self.active and not willing_to_trade(tradeprice):
                    # wouldnt have got this deal, still working order, so reduce margin
                    target_price = target_up(tradeprice)
                    profit_alter(target_price)
            else:
                # no deal: aim for target price lower than best ask
                if bid_improved and self.price < lob_best_bid_p:
                    if lob_best_ask_p is not None:
                        target_price = target_down(lob_best_ask_p)
                    else:
                        target_price = lob['bids']['worst']  # stub quote
                    profit_alter(target_price)

        # remember the best LOB data ready for next response
        self.prev_best_bid_p = lob_best_bid_p
        self.prev_best_bid_q = lob_best_bid_q
        self.prev_best_ask_p = lob_best_ask_p
        self.prev_best_ask_q = lob_best_ask_q





    def mutate(self, time, lob, trade, verbose):
        return




        