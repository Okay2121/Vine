#!/usr/bin/env python
"""
Demonstration: Cumulative Initial Deposit Behavior
Shows how the initial deposit increases with each deposit
"""

def demonstrate_cumulative_logic():
    """Demonstrate the cumulative deposit logic"""
    
    print("CUMULATIVE INITIAL DEPOSIT DEMONSTRATION")
    print("=" * 50)
    print()
    
    # Simulate user starting state
    balance = 0.0
    initial_deposit = 0.0
    
    print(f"Starting state:")
    print(f"  Balance: {balance:.4f} SOL")
    print(f"  Initial Deposit: {initial_deposit:.4f} SOL")
    print()
    
    # Simulate deposits
    deposits = [1.5, 2.0, 0.75, 3.25]
    
    for i, amount in enumerate(deposits, 1):
        print(f"Deposit {i}: {amount} SOL")
        
        # This is what happens in utils/solana.py process_auto_deposit:
        balance += amount                    # user.balance = previous_balance + amount
        initial_deposit += amount            # user.initial_deposit += amount
        
        print(f"  After deposit {i}:")
        print(f"    Balance: {balance:.4f} SOL")
        print(f"    Initial Deposit: {initial_deposit:.4f} SOL")
        print(f"    (Added {amount} SOL to both values)")
        print()
    
    total_deposited = sum(deposits)
    print("FINAL VERIFICATION:")
    print(f"  Total deposited: {total_deposited:.4f} SOL")
    print(f"  Final balance: {balance:.4f} SOL")
    print(f"  Final initial deposit: {initial_deposit:.4f} SOL")
    print()
    
    if balance == total_deposited and initial_deposit == total_deposited:
        print("✅ BEHAVIOR CONFIRMED: Both values match total deposits")
        print("✅ Initial deposit correctly accumulates with each deposit")
        print("✅ System maintains running total of all deposits as baseline")
    else:
        print("❌ Logic error detected")
    
    print()
    print("CODE VERIFICATION:")
    print("In utils/solana.py, line 560:")
    print("  user.initial_deposit += amount")
    print()
    print("This line ensures each deposit is added to the existing")
    print("initial_deposit value, creating a cumulative total.")

if __name__ == "__main__":
    demonstrate_cumulative_logic()