import pandas
import matplotlib.pyplot

'''
This function plots the data related to one transaction file.
The parameters are:
  - The path where the file is
  - The equilibrium price (optional)
'''
def plot_single_transactions_session(file_path, equilibrium=None):
    pdf_name = file_path.split(".")
    data = pandas.read_csv(file_path, header=None)
    data.columns = ["Type", "Time", "Prices"]
    ax = matplotlib.pyplot.gca()
    data.plot(kind="line", x="Time", y="Prices", ax=ax)

    if equilibrium is not None:

        matplotlib.pyplot.axhline(y=equilibrium, linewidth=1.71, linestyle=":", color='k', label="Equilibrium price")

    ax.set_xlabel("Time")
    ax.set_ylabel("Prices")
    ax.set_title(pdf_name[0])
    ax.legend()
   
    matplotlib.pyplot.savefig(fname=pdf_name[0]+".jpg", orientation="portrait")
    matplotlib.pyplot.show()

'''
This function plots the data related to more than one transaction files.
The parameters are:
  - An array where the file paths are
  - The equilibrium price (optional)
'''
def plot_multiple_transactions_sessions(file_paths, equilibrium=None):
    pdf_names = []
    ax = matplotlib.pyplot.gca()

    for file_path in file_paths:
        pdf_name = file_path.split(".")
        pdf_names.append(pdf_name[0])
        data = pandas.read_csv(file_path, header=None)
        data.columns = ["Type", "Time", "Prices"]
        matplotlib.pyplot.show()
        data.plot(kind="line", x="Time", y="Prices", ax=ax, label=pdf_name[0])

    if equilibrium is not None:

        matplotlib.pyplot.axhline(y=equilibrium, linewidth=1.71, linestyle=":", color='k', label="Equilibrium price")

    ax.set_xlabel("Time")
    ax.set_ylabel("Prices")
    ax.set_title("Sessions transactions")
    ax.legend()
    matplotlib.pyplot.savefig(fname="Sessions_transactions.pdf", orientation="portrait")


if __name__ == "__main__":

    single = True

    if single:

        path = "sess0001_transactions.csv"
        plot_single_transactions_session(path)

    else:
        paths = ["sess0001_transactions.csv",
                 "sess0002_transactions.csv",
                 "sess0003_transactions.csv"
                 ]

        plot_multiple_transactions_sessions(paths, 100)
