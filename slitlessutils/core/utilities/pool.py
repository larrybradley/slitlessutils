import multiprocessing as mp
from functools import partial

import psutil as ps
import tqdm

from ...logger import LOGGER


class Pool:
    """
    A pool class to give more (and more useful) options to the user
    """

    def __init__(self, func, ncpu=None, desc=''):
        """
        Initializer

        Parameters
        ----------
        func : callable
            The function to iterate many times

        ncpu : int or None, optional
            The number of CPUs to use.  If set to None, then the number
            will be computed, but leave 1 CPU unused.  Default is None

        desc : str, optional
            The name to precede the `tqdm.tqdm()` progress bar.  Default
            is ''

        """

        # get some settings for the processing
        ncpus = ps.cpu_count(logical=False)
        ncores = ps.cpu_count(logical=True)
        nthreads = ncores // ncpus
        nmax = ncpus - nthreads

        # set a default to the max
        if ncpu is None or ncpu <= 0:
            self.ncpu = nmax
        else:
            self.ncpu = min(max(ncpu, 1), nmax)    # force this to be in range
        self.desc = desc
        self.func = func

    def __zip__(self, itrs, *args):
        """
        A generator to zip iterables with scalars

        Should never be explicitly used.

        Parameters
        ----------
        itrs : iterable
            The thing to iterate over

        args : tuple
            A tuple of the scalar values to zip with the itrs

        Returns
        -------
        tuple of a single itr and the args.

        Notes
        -----
        This might be the same as things in `functools`

        """
        for itr in itrs:
            yield (itr, *args)

    def __worker__(self, args):
        """
        Method to unpack the arguments to send to the function

        Should never be explicitly called
        """
        return self.func(*args)

    # def __enter__(self):
    #    return self

    # def __exit__(self,etype,eval,etb):
    #    pass

    def __str__(self):
        lines = ['Pool object with:',
                 f'NCPU = {self.ncpu}',
                 f'FUNC = {self.func}']
        return '\n'.join(lines)

    def __call__(self, itrs, *args, total=None, **kwargs):
        """
        Method to start/run the Pool

        Parameters
        ----------
        itrs : iterables
            The items to iterate over in the pool

        args : tuple
            Scalar values to glue to each iteration

        total : int or None, optional
            The total number of iterates for the pool to work on.  This is
            used for printing purposes only.  If set to `None`, then the
            length of the `itrs` array is used.  Default is None

        kwargs : dict, optional
            optional keywords to pass to the iterating function.

        Returns
        -------
        results : list
            A list of the outputs generated by the iterating function.
            These will be in the *SAME* order as the `itrs` array

        """

        # number of iterations to do
        if total is None:
            total = len(itrs)

        # get the number of CPUs to use
        ncpu = min(total, self.ncpu)

        # start multiprocessing as necessary
        if ncpu == 1:
            LOGGER.info('Serial processing')
            results = [self.func(i, *args, **kwargs) for i in
                       tqdm.tqdm(itrs, total=total, desc=self.desc)]

        else:
            LOGGER.info(f'Parallel processing: {total} jobs with {ncpu} processes')

            if kwargs:
                func = self.func    # save it for later
                self.func = partial(self.func, **kwargs)

            # actually start the processing pool:
            with mp.Pool(processes=ncpu) as p:
                imap = p.imap(self.__worker__, self.__zip__(itrs, *args))
                results = list(tqdm.tqdm(imap, total=total, desc=self.desc))

            # func=partial(self.func,**kwargs)
            # print(func)
            # p=mp.Pool(processes=self.ncpu)
            # imap=p.map(func,self.__zip__(itrs,*args))
            # results=list(tqdm.tqdm(imap,total=total,desc=self.desc))

            if kwargs:
                self.func = func   # reset it

        return results
