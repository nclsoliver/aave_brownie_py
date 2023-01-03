from brownie import network, config, interface
from scripts.helpful_scripts import get_account
from scripts.get_weth import get_weth
from web3 import Web3

# 0.1
amount = Web3.toWei(0.1, "ether")


def main():
    account = get_account()
    erc20_address = config["networks"][network.show_active()]["weth_token"]
    if network.show_active() in ["mainnet-fork"]:
        get_weth(account=account)
    lending_pool = get_lending_pool()
    approve_erc20(amount, lending_pool.address, erc20_address, account)
    print("Depositing...")
    lending_pool.deposit(erc20_address, amount, account.address, 0, {"from": account})
    print("Deposited!")
    borrowable_eth, total_debt_eth = get_borrowable_data(lending_pool, account)
    print("Let's borrow!")
    # Link in terms of ETH
    link_eth_price_feed = get_asset_price(
        config["networks"][network.show_active()]["link_eth_price_feed"]
    )
    amount_link_to_borrow = (1 / link_eth_price_feed) * (borrowable_eth * 0.95)
    # borrowable_eth -> borrowable_link * 95%\
    print(f"We are going to borrow {amount_link_to_borrow} LINK")
    # Now we will borrow!
    link_address = config["networks"][network.show_active()]["link_token"]
    borrow_tx = lending_pool.borrow(
        link_address,
        Web3.toWei(amount_link_to_borrow, "ether"),
        1,
        0,
        account.address,
        {"from": account},
    )
    borrow_tx.wait(1)
    print(" We borrow some LINK!")
    get_borrowable_data(lending_pool, account)
    repay_all(amount, lending_pool, account)
    print("You just deposited, borrowed and repaid with Aave, Brownie and Chainlink!")


def repay_all(amount, lending_pool, account):
    approve_erc20(
        Web3.toWei(amount, "ether"),
        lending_pool,
        config["networks"][network.show_active()]["link_token"],
        account,
    )
    repay_tx = lending_pool.repay(
        config["networks"][network.show_active()]["link_token"],
        amount,
        1,
        account.address,
        {"from": account},
    )
    repay_tx.wait(1)
    print("Repaid!")


def get_asset_price(price_feed_address):
    # For mainnet we can just do:
    # return Contract(f"{pair}.data.eth").latestAnswer() / 1e8
    link_eth_price_feed = interface.AggregatorV3Interface(
        config["networks"][network.show_active()]["link_eth_price_feed"]
    )
    latest_price = Web3.fromWei(link_eth_price_feed.latestRoundData()[1], "ether")
    print(f"The LINK/ETH price is {latest_price}")
    return float(latest_price)


def get_borrowable_data(lending_pool, account):
    (
        total_collateral_eth,
        total_debt_eth,
        avaible_barrow_eth,
        current_liquidation_threshold,
        ltv,
        health_factor,
    ) = lending_pool.getUserAccountData(account.address)
    avaible_barrow_eth = Web3.fromWei(avaible_barrow_eth, "ether")
    total_collateral_eth = Web3.fromWei(total_collateral_eth, "ether")
    total_debt_eth = Web3.fromWei(total_debt_eth, "ether")
    print(f"You have {total_collateral_eth} worth of ETH deposited.")
    print(f"You have {total_debt_eth} worth of ETH borrowed.")
    print(f"You can borrow {avaible_barrow_eth} worth of ETH.")
    return (float(avaible_barrow_eth), float(total_debt_eth))


def approve_erc20(amount, spender, erc20_address, account):
    print("Approving ERC20 token...")
    erc20 = interface.IERC20(erc20_address)
    tx = erc20.approve(spender, amount, {"from": account})
    tx.wait(1)
    print("Approved!")
    return tx


def get_lending_pool():
    lending_pool_addresses_provider = interface.ILendingPoolAddressesProvider(
        config["networks"][network.show_active()]["lending_pool_addresses_provider"]
    )
    lending_pool_address = lending_pool_addresses_provider.getLendingPool()
    # ABI
    # Address - Check!
    lending_pool = interface.ILendingPool(lending_pool_address)
    return lending_pool
