namespace Freeform.Rigging.MessageDialogue
{
    using System;
    using System.ComponentModel;
    using System.Diagnostics;
    using System.Windows;
    using System.Windows.Interop;

    using Freeform.Core.UI;

    /// <summary>
    /// Interaction logic for MessageDialogue.xaml
    /// </summary>
    public partial class MessageDialogue : Window
    {
        public MessageDialogue()
        {
            InitializeComponent();
            SetupDataContext();
        }

        public MessageDialogue(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }

        void SetupDataContext()
        {
            DispatcherHelper.UIDispatcher = Dispatcher;

            MessageDialogueVM vm = new MessageDialogueVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            MessageDialogueVM vm = DataContext as MessageDialogueVM;
            vm.Close();
        }
    }
}
